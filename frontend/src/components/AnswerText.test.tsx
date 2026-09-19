import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import { AnswerText } from "./AnswerText";

it("turns [n] and [n, m] into buttons that select the source", async () => {
  const onCite = vi.fn();
  render(<AnswerText text="It carries 4 credits [1][2, 3]." onCite={onCite} />);
  expect(screen.getAllByRole("button")).toHaveLength(3);
  await userEvent.click(screen.getByRole("button", { name: "Show source 3" }));
  expect(onCite).toHaveBeenCalledWith(3);
  expect(screen.getByText(/It carries 4 credits/)).toBeInTheDocument();
});

it("never renders answer text as HTML", () => {
  render(<AnswerText text={'<img src="x" onerror="alert(1)"> [1]'} onCite={() => {}} />);
  expect(document.querySelector("img")).toBeNull();
  expect(screen.getByText(/<img src="x"/)).toBeInTheDocument();
});
