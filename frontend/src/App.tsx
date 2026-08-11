import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { getToken } from "./lib/api";
import { ActivityEdit } from "./pages/ActivityEdit";
import { AuthCallback } from "./pages/AuthCallback";
import { Calendar } from "./pages/Calendar";
import { Login } from "./pages/Login";
import { Settings } from "./pages/Settings";
import { Today } from "./pages/Today";

function Protegida({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  if (!getToken()) return <Navigate to="/login" replace state={{ from: location }} />;
  return <>{children}</>;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      <Route
        path="/"
        element={
          <Protegida>
            <Today />
          </Protegida>
        }
      />
      <Route
        path="/dia/:date"
        element={
          <Protegida>
            <Today />
          </Protegida>
        }
      />
      <Route
        path="/calendario"
        element={
          <Protegida>
            <Calendar />
          </Protegida>
        }
      />
      <Route
        path="/atividade/:id"
        element={
          <Protegida>
            <ActivityEdit />
          </Protegida>
        }
      />
      <Route
        path="/ajustes"
        element={
          <Protegida>
            <Settings />
          </Protegida>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
