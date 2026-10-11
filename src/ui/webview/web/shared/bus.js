// git-sentinel - tiny pub/sub mirroring the Python-side EventBus, so pages
// can subscribe to pushed events without caring how dispatch() delivers them.
(function () {
  const listeners = {};

  window.bus = {
    on(event, fn) {
      (listeners[event] = listeners[event] || []).push(fn);
    },
    dispatch(event, data) {
      (listeners[event] || []).forEach((fn) => fn(data));
    },
  };
})();
