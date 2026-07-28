import { inject, onBeforeUnmount, onMounted } from "vue";
import { matchedRouteKey, onBeforeRouteLeave } from "vue-router";
import type { Ref } from "vue";

export function useUnsavedChanges(dirty: Ref<boolean>) {
  const warnBeforeUnload = (event: BeforeUnloadEvent) => {
    if (!dirty.value) return;
    event.preventDefault();
    event.returnValue = "";
  };

  onMounted(() => window.addEventListener("beforeunload", warnBeforeUnload));
  onBeforeUnmount(() => window.removeEventListener("beforeunload", warnBeforeUnload));
  if (inject(matchedRouteKey, null)) {
    onBeforeRouteLeave(() => !dirty.value || window.confirm("尚有未保存的修改，仍要离开吗？"));
  }
}
