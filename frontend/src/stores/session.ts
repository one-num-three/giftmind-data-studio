import { defineStore } from "pinia";

import { apiRequest } from "../api/client";
import type { SessionResponse } from "../api/types";

interface SessionState {
  authenticated: boolean;
  expiresAt: string | null;
  restored: boolean;
}

export const useSessionStore = defineStore("session", {
  state: (): SessionState => ({
    authenticated: false,
    expiresAt: null,
    restored: false,
  }),

  actions: {
    applySession(session: SessionResponse) {
      this.authenticated = session.authenticated;
      this.expiresAt = session.expiresAt;
    },

    clear() {
      this.authenticated = false;
      this.expiresAt = null;
    },

    async restore() {
      try {
        this.applySession(await apiRequest<SessionResponse>("/api/session", {
          handleUnauthorized: false,
        }));
      } catch {
        this.clear();
      } finally {
        this.restored = true;
      }
    },

    async login(passcode: string) {
      this.applySession(await apiRequest<SessionResponse>("/api/session/login", {
        method: "POST",
        body: { passcode },
      }));
    },

    async logout() {
      try {
        await apiRequest<void>("/api/session/logout", { method: "POST" });
      } finally {
        this.clear();
      }
    },
  },
});
