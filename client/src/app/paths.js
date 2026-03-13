export const ROUTES = {
  home: "/",
  register: "/register",
  login: "/login",
  verify: "/auth/verify",
  dashboard: "/dashboard",
  visibility: "/visibility",
  accuracy: "/accuracy",
  competitors: "/competitors",
  actions: "/actions",
};

export const DASHBOARD_NAV_ITEMS = [
  { label: "Dashboard", path: ROUTES.dashboard, api: "/api/dashboard/*" },
  { label: "Visibility", path: ROUTES.visibility, api: "/api/visibility/*" },
  { label: "Accuracy", path: ROUTES.accuracy, api: "/api/accuracy/*" },
  { label: "Competitors", path: ROUTES.competitors, api: "/api/competitors/*" },
  { label: "Actions", path: ROUTES.actions, api: "/api/actions/*" },
];
