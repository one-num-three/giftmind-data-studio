import { createRouter, createWebHistory } from "vue-router";

import AppShell from "../components/layout/AppShell.vue";
import DashboardView from "../views/DashboardView.vue";
import GiftListView from "../views/GiftListView.vue";
import GiftWorkbenchView from "../views/GiftWorkbenchView.vue";
import LoginView from "../views/LoginView.vue";
import RecycleBinView from "../views/RecycleBinView.vue";
import ToolsView from "../views/ToolsView.vue";
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
        {
          path: "gifts",
          name: "gift-list",
          component: GiftListView,
        },
        {
          path: "gifts/new",
          name: "gift-create",
          component: GiftWorkbenchView,
        },
        {
          path: "gifts/:giftId",
          name: "gift-edit",
          component: GiftWorkbenchView,
          props: (route) => ({ giftId: route.params.giftId }),
        },
        {
          path: "recycle-bin",
          name: "recycle-bin",
          component: RecycleBinView,
        },
        { path: "tools", name: "tools", component: ToolsView },
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
