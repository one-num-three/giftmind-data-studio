import { createRouter, createWebHistory } from "vue-router";

import AppShell from "../components/layout/AppShell.vue";
import DashboardView from "../views/DashboardView.vue";
import LoginView from "../views/LoginView.vue";
import { useSessionStore } from "../stores/session";

declare module "vue-router" {
  interface RouteMeta {
    requiresAuth?: boolean;
  }
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/login",
      name: "login",
      component: LoginView,
    },
    {
      path: "/",
      component: AppShell,
      meta: { requiresAuth: true },
      children: [
        {
          path: "",
          name: "dashboard",
          component: DashboardView,
        },
      ],
    },
  ],
});

router.beforeEach(async (to) => {
  const session = useSessionStore();

  if (!session.restored) {
    await session.restore();
  }

  if (to.meta.requiresAuth && !session.authenticated) {
    return { name: "login" };
  }

  if (to.name === "login" && session.authenticated) {
    return { name: "dashboard" };
  }
});

export default router;
