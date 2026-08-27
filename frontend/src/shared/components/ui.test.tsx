import { MemoryRouter } from "react-router-dom";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorAlert,
  FormField,
  Input,
  LinkButton,
  LoadingState,
  Notice,
  PageHeader,
  Select,
  TextArea,
} from ".";

describe("LibraryOS shared UI vocabulary", () => {
  it("renders reusable controls and explicit feedback states", () => {
    render(
      <MemoryRouter future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
        <PageHeader actions={<Button>Action</Button>} description="A short description" title="Catalog" />
        <Card data-testid="card">Card content</Card>
        <Badge variant="accent">Featured</Badge>
        <FormField htmlFor="title" label="Title" hint="Required">
          <Input id="title" />
        </FormField>
        <FormField htmlFor="category" label="Category">
          <Select id="category"><option>All</option></Select>
        </FormField>
        <FormField htmlFor="description" label="Description">
          <TextArea id="description" />
        </FormField>
        <LinkButton to="/books">Browse books</LinkButton>
        <LoadingState title="Loading" />
        <EmptyState detail="Nothing here yet." title="Empty" />
        <ErrorAlert message="Something went wrong" />
        <Notice message="Saved" />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Catalog" })).toBeInTheDocument();
    expect(screen.getByTestId("card")).toHaveTextContent("Card content");
    expect(screen.getByText("Featured")).toBeInTheDocument();
    expect(screen.getByLabelText("Title")).toBeInTheDocument();
    expect(screen.getByLabelText("Category")).toBeInTheDocument();
    expect(screen.getByLabelText("Description")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Browse books" })).toHaveAttribute("href", "/books");
    expect(screen.getByRole("alert")).toHaveTextContent("Something went wrong");
    expect(screen.getByText("Saved")).toBeInTheDocument();
  });

  it("makes a loading action unavailable and exposes its busy state", () => {
    render(<Button loading>Saving</Button>);

    expect(screen.getByRole("button", { name: "Saving" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Saving" })).toHaveAttribute("aria-busy", "true");
  });
});
