// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";

describe("Field", () => {
  it("labels the control and reads the hint and error to screen readers", () => {
    render(
      <Field
        label="Work email"
        hint="We send invites here."
        error="Enter an email address."
        required
      >
        <Input type="email" />
      </Field>,
    );
    const input = screen.getByLabelText("Work email");
    expect(input).toHaveAccessibleDescription("We send invites here. Enter an email address.");
    expect(input).toBeInvalid();
    expect(input).toBeRequired();
    expect(screen.getByRole("alert")).toHaveTextContent("Enter an email address.");
  });

  it("marks the control valid when there is no error", () => {
    render(
      <Field label="Role title">
        <Input />
      </Field>,
    );
    const input = screen.getByLabelText("Role title");
    expect(input).toBeValid();
    expect(input).not.toHaveAttribute("aria-describedby");
  });
});
