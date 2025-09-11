import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ToastContainer } from "react-toastify";
import { ChatProvider } from "./contexts/ChatContext";
import GlobalChatWidget from "./components/GlobalChatWidget";
import Index from "./pages";
import "react-toastify/dist/ReactToastify.css";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <ChatProvider>
      <BrowserRouter>
        <div className="pb16">
          <Routes>
            <Route path="/" element={<Index />} />
            {/* <Route path="*" element={<NotFound />} /> */}
          </Routes>
        </div>
        <ToastContainer
          position="bottom-right"
          autoClose={3000}
          hideProgressBar={false}
          newestOnTop={false}
          closeOnClick
          rtl={false}
          pauseOnFocusLoss
          draggable
          pauseOnHover
          theme="dark"
        />
        <GlobalChatWidget />
      </BrowserRouter>
    </ChatProvider>
  </QueryClientProvider>
);

export default App;
