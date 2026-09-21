import { config } from "@vue/test-utils";

config.global.stubs = {
  VAppBar: { template: "<header><slot /></header>" },
  VNavigationDrawer: { template: "<aside><slot /></aside>" },
  VDialog: {
    props: ["modelValue"],
    template: '<div v-if="modelValue" class="v-dialog-stub"><slot /></div>',
  },
};

if (typeof globalThis.ResizeObserver === "undefined") {
  class ResizeObserverMock {
    observe() {}
    unobserve() {}
    disconnect() {}
  }

  globalThis.ResizeObserver = ResizeObserverMock as typeof ResizeObserver;
}

if (typeof globalThis.visualViewport === "undefined") {
  globalThis.visualViewport = {
    width: 1024,
    height: 768,
    offsetTop: 0,
    offsetLeft: 0,
    addEventListener() {},
    removeEventListener() {},
  } as typeof visualViewport;
}
