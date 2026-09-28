// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Field } from "@/components/ui/field";
import { NumberStepper } from "@/components/ui/number-stepper";

function renderStepper(defaultValue: number) {
  const onValueChange = vi.fn();
  render(
    <Field label="Credits to buy">
      <NumberStepper
        defaultValue={defaultValue}
        onValueChange={onValueChange}
        min={10}
        max={50}
        step={10}
        unit="credits"
      />
    </Field>,
  );
  return {
    input: screen.getByLabelText("Credits to buy"),
    add: screen.getByRole("button", { name: "Add 10 credits" }),
    remove: screen.getByRole("button", { name: "Remove 10 credits" }),
    onValueChange,
  };
}

describe("NumberStepper", () => {
  it("steps and stops at the maximum", async () => {
    const user = userEvent.setup();
    const { input, add, onValueChange } = renderStepper(40);
    await user.click(add);
    expect(input).toHaveValue("50");
    expect(onValueChange).toHaveBeenLastCalledWith(50);
    expect(add).toBeDisabled();
  });

  it("disables remove at the minimum", () => {
    const { remove } = renderStepper(10);
    expect(remove).toBeDisabled();
  });

  it("clamps typed values into range", async () => {
    const user = userEvent.setup();
    const { input, onValueChange } = renderStepper(20);
    await user.clear(input);
    await user.type(input, "999{Enter}");
    expect(input).toHaveValue("50");
    await user.clear(input);
    await user.type(input, "3{Enter}");
    expect(input).toHaveValue("10");
    expect(onValueChange).toHaveBeenLastCalledWith(10);
  });
});
