// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { TypeToConfirmDialog } from "@/components/ui/dialog";

function renderDialog(onConfirm = vi.fn()) {
  render(
    <TypeToConfirmDialog
      open
      onOpenChange={() => undefined}
      title="Delete Acme workspace?"
      description="This can't be undone."
      phrase="I understand"
      confirmLabel="Delete workspace"
      onConfirm={onConfirm}
    />,
  );
  return {
    input: screen.getByLabelText("Type “I understand” to confirm"),
    confirm: screen.getByRole("button", { name: "Delete workspace" }),
    onConfirm,
  };
}

describe("TypeToConfirmDialog", () => {
  it("stays disabled until the exact phrase is typed", async () => {
    const user = userEvent.setup();
    const { input, confirm } = renderDialog();
    expect(confirm).toBeDisabled();

    for (const attempt of ["i understand", "I understand ", "I understan"]) {
      await user.clear(input);
      await user.type(input, attempt);
      expect(confirm).toBeDisabled();
    }

    await user.clear(input);
    await user.type(input, "I understand");
    expect(confirm).toBeEnabled();
  });

  it("confirms once the phrase matches", async () => {
    const user = userEvent.setup();
    const { input, confirm, onConfirm } = renderDialog();
    await user.type(input, "I understand");
    await user.click(confirm);
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });
});
