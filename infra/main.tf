terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# --- Cloud SQL (PostgreSQL) ---

resource "google_sql_database_instance" "protocrawl" {
  name             = "protocrawl-db"
  database_version = "POSTGRES_16"
  region           = var.region

  settings {
    tier              = var.db_tier
    availability_type = "ZONAL"

    ip_configuration {
      ipv4_enabled = false
      private_network = google_compute_network.protocrawl.id
    }

    backup_configuration {
      enabled    = true
      start_time = "03:00"
    }
  }

  deletion_protection = true
}

resource "google_sql_database" "protocrawl" {
  name     = "protocrawl"
  instance = google_sql_database_instance.protocrawl.name
}

resource "google_sql_user" "protocrawl" {
  name     = "protocrawl"
  instance = google_sql_database_instance.protocrawl.name
  password = var.db_password
}

# --- VPC for Cloud SQL private IP ---

resource "google_compute_network" "protocrawl" {
  name                    = "protocrawl-network"
  auto_create_subnetworks = true
}

resource "google_compute_global_address" "private_ip" {
  name          = "protocrawl-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.protocrawl.id
}

resource "google_service_networking_connection" "private_vpc" {
  network                 = google_compute_network.protocrawl.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip.name]
}

# --- Cloud Storage ---

resource "google_storage_bucket" "artifacts" {
  name          = "${var.project_id}-protocrawl-artifacts"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 365
    }
  }
}

# --- Artifact Registry for Docker images ---

resource "google_artifact_registry_repository" "protocrawl" {
  location      = var.region
  repository_id = "protocrawl"
  format        = "DOCKER"
}

# --- Service Account ---

resource "google_service_account" "protocrawl" {
  account_id   = "protocrawl-api"
  display_name = "Protocrawl API Service Account"
}

resource "google_project_iam_member" "sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.protocrawl.email}"
}

resource "google_project_iam_member" "storage_admin" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.protocrawl.email}"
}

resource "google_project_iam_member" "vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.protocrawl.email}"
}

# --- Cloud Run (API) ---

resource "google_cloud_run_v2_service" "api" {
  name     = "protocrawl-api"
  location = var.region

  template {
    service_account = google_service_account.protocrawl.email

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/protocrawl/api:latest"

      ports {
        container_port = 8000
      }

      env {
        name  = "PROTOCRAWL_GCP_PROJECT"
        value = var.project_id
      }
      env {
        name  = "PROTOCRAWL_GCP_LOCATION"
        value = var.region
      }
      env {
        name  = "PROTOCRAWL_GCS_BUCKET"
        value = google_storage_bucket.artifacts.name
      }
      env {
        name  = "PROTOCRAWL_DATABASE_URL"
        value = "postgresql+asyncpg://protocrawl:${var.db_password}@/protocrawl?host=/cloudsql/${google_sql_database_instance.protocrawl.connection_name}"
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      startup_probe {
        http_get {
          path = "/health"
        }
      }
    }

    vpc_access {
      network_interfaces {
        network = google_compute_network.protocrawl.name
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }
  }
}

# Allow unauthenticated access to the API
resource "google_cloud_run_v2_service_iam_member" "public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# --- Cloud Scheduler (weekly Source Scout) ---

resource "google_cloud_scheduler_job" "source_scout" {
  name     = "protocrawl-source-scout"
  schedule = "0 6 * * 1" # Every Monday at 6 AM
  timezone = "America/New_York"

  http_target {
    uri         = "${google_cloud_run_v2_service.api.uri}/pipeline/run"
    http_method = "POST"

    oidc_token {
      service_account_email = google_service_account.protocrawl.email
    }
  }
}

# --- Outputs ---

output "api_url" {
  value = google_cloud_run_v2_service.api.uri
}

output "db_connection_name" {
  value = google_sql_database_instance.protocrawl.connection_name
}

output "artifacts_bucket" {
  value = google_storage_bucket.artifacts.name
}

output "docker_registry" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/protocrawl"
}
