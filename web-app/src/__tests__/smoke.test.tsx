import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

function HelloCard({ name }: { name: string }) {
  return (
    <div>
      <h1>Welcome back, {name}</h1>
      <p>Hissabi is ready when you are.</p>
    </div>
  );
}

describe("HelloCard", () => {
  it("renders the welcome heading with the given name", () => {
    render(<HelloCard name="Cedric" />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "Welcome back, Cedric"
    );
  });
});
