import { createApp } from "vue";
import { createPinia } from "pinia";

import App from "./App.vue";
import { setUnauthorizedHandler } from "./api/client";
import router from "./router";
import { useSessionStore } from "./stores/session";
import "./styles/tokens.css";

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);

setUnauthorizedHandler(async () => {
  useSessionStore(pinia).clear();
  if (router.currentRoute.value.name !== "login") {
    await router.replace({ name: "login" });
  }
});

app.use(router);
app.mount("#app");
