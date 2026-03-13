import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "../components/layout/ProtectedRoute";
import DashboardLayout from "../components/layout/DashboardLayout";
import { ROUTES } from "./paths";
import HomePage from "../pages/HomePage";
import RegisterPage from "../features/auth/pages/RegisterPage";
import LoginPage from "../features/auth/pages/LoginPage";
import VerifyPage from "../features/auth/pages/VerifyPage";
import DashboardOverviewPage from "../features/dashboard/pages/DashboardOverviewPage";
import VisibilityPage from "../features/visibility/pages/VisibilityPage";
import AccuracyPage from "../features/accuracy/pages/AccuracyPage";
import CompetitorsPage from "../features/competitors/pages/CompetitorsPage";
import ActionsPage from "../features/actions/ActionsPage";

export default function AppRouter() {
  return (
    <Routes>
      <Route path={ROUTES.home} element={<HomePage />} />
      <Route path={ROUTES.register} element={<RegisterPage />} />
      <Route path={ROUTES.login} element={<LoginPage />} />
      <Route path={ROUTES.verify} element={<VerifyPage />} />

      <Route
        element={(
          <ProtectedRoute>
            <DashboardLayout />
          </ProtectedRoute>
        )}
      >
        <Route path={ROUTES.dashboard} element={<DashboardOverviewPage />} />
        <Route path={ROUTES.visibility} element={<VisibilityPage />} />
        <Route path={ROUTES.accuracy} element={<AccuracyPage />} />
        <Route path={ROUTES.competitors} element={<CompetitorsPage />} />
        <Route path={ROUTES.actions} element={<ActionsPage />} />
      </Route>

      <Route path="*" element={<Navigate to={ROUTES.home} replace />} />
    </Routes>
  );
}
