import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AppShell } from "@/components/AppShell";
import ProtocolsPage from "./pages/ProtocolsPage";
import ProtocolDetailPage from "./pages/ProtocolDetailPage";
import ReviewDetailPage from "./pages/ReviewDetailPage";
import ReviewsPage from "./pages/ReviewsPage";
import SubmissionsPage from "./pages/SubmissionsPage";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <AppShell>
          <Routes>
            <Route path="/" element={<ProtocolsPage />} />
            <Route path="/protocols/:slug" element={<ProtocolDetailPage />} />
            <Route path="/reviews" element={<ReviewsPage />} />
            <Route path="/reviews/:reviewId" element={<ReviewDetailPage />} />
            <Route path="/submissions" element={<SubmissionsPage />} />
            {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </AppShell>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
