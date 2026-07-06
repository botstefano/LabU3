import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { LoadingState } from "./ui/States";

export default function ProtectedRoute({ children, roles }) {
  const { user, loading } = useAuth();

  if (loading) return <LoadingState label="Verificando sesión..." />;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.rol)) return <Navigate to="/" replace />;

  return children;
}
