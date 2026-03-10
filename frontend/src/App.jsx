import Login from "./components/login";
import { Navigate, Route, Routes } from "react-router-dom";
import PlaceholderPage from "./pages/PlaceholderPage";
import WeighmentPage from "./pages/WeighmentPage";

export default function App() {
  return (
    <main className="app-shell">
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<Login />} />
        <Route path="/weighment" element={<WeighmentPage />} />
        <Route
          path="/master"
          element={
            <PlaceholderPage
              title="Master"
              description="Customer, vehicle, operator and configuration masters will be managed here."
            />
          }
        />
        <Route
          path="/sms"
          element={
            <PlaceholderPage
              title="SMS Center"
              description="SMS resend history and delivery actions will be shown here."
            />
          }
        />
        <Route
          path="/reports"
          element={
            <PlaceholderPage
              title="Reports"
              description="Date-wise, customer-wise, material-wise and truck-wise reports will be rendered here."
            />
          }
        />
        <Route
          path="/live-view"
          element={
            <PlaceholderPage
              title="Live View"
              description="All camera feeds and operational monitoring widgets will be displayed here."
            />
          }
        />
      </Routes>
    </main>
  );
}

