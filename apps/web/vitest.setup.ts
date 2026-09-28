import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Component tests opt into jsdom with `// @vitest-environment jsdom`; unmount between tests.
afterEach(() => {
  if (typeof document !== "undefined") cleanup();
});
