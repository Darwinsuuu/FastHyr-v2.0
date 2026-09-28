// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import { Pagination } from "@/components/ui/pagination";

function Harness({ start = 1 }: { start?: number }) {
  const [page, setPage] = useState(start);
  return (
    <Pagination total={42} page={page} pageSize={10} onPageChange={setPage} noun="pipelines" />
  );
}

describe("Pagination", () => {
  it("changes page and stops at the last one", async () => {
    const user = userEvent.setup();
    render(<Harness start={4} />);
    expect(screen.getByText("Showing 31–40 of 42 pipelines")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByText("Showing 41–42 of 42 pipelines")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Page 5" })).toHaveAttribute("aria-current", "page");
  });

  it("disables Prev on the first page and jumps to a numbered page", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    expect(screen.getByRole("button", { name: "Prev" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Page 3" }));
    expect(screen.getByText("Page 3 of 5")).toBeInTheDocument();
  });
});
