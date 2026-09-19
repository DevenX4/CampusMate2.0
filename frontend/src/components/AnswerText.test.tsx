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

it("shows each cited statement as a paragraph, with synthetic statements labelled", () => {
  const text = "AI carries 4 credits [1]. (Synthetic demo data) Dr. Example teaches it [2]. Synthetic demo data is not official GUNI information.";
  const { container } = render(<AnswerText text={text} onCite={() => {}} omit="Synthetic demo data is not official GUNI information." />);
  expect((container.firstChild as HTMLElement).children).toHaveLength(2);
  expect(screen.getByText("Synthetic demo")).toBeInTheDocument();
  expect(screen.queryByText(/\(Synthetic demo data\)/)).toBeNull();
  expect(screen.queryByText(/not official GUNI information/)).toBeNull();  // shown as a note instead
});

it("shortens a long statement whose evidence is shown as a table, and can show it in full", async () => {
  const list = Array.from({ length: 12 }, (_, i) => `2CEIT6${i} COURSE ${i} (4 cr)`).join("; ");
  render(<AnswerText text={`B.TECH-IT Semester VI (23 credits in total): regular courses: ${list} [1].`} onCite={() => {}} tabled={[1]} />);
  expect(screen.getByText("B.TECH-IT Semester VI (23 credits in total)")).toBeInTheDocument();
  expect(screen.queryByText(/COURSE 11/)).toBeNull();
  await userEvent.click(screen.getByRole("button", { name: "Show as text" }));
  expect(screen.getByText(/COURSE 11/)).toBeInTheDocument();
});
