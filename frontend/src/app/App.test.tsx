import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "./App";

describe("LibraryOS frontend foundation", () => {
  it("mounts the application shell and renders the product name", () => {
    render(<App />);

    expect(screen.getByText(/LibraryOS/i)).toBeTruthy();
  });
});
