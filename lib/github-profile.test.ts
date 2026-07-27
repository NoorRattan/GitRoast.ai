import { describe, expect, it } from "vitest";
import { normalizeGitHubProfileInput } from "./github-profile";

describe("normalizeGitHubProfileInput", () => {
  it("keeps valid GitHub usernames for existing shared URLs", () => {
    expect(normalizeGitHubProfileInput("NoorRattan")).toBe("NoorRattan");
    expect(normalizeGitHubProfileInput("torvalds")).toBe("torvalds");
  });

  it("extracts usernames from GitHub profile links", () => {
    expect(normalizeGitHubProfileInput("https://github.com/NoorRattan")).toBe("NoorRattan");
    expect(normalizeGitHubProfileInput("github.com/NoorRattan?tab=repositories")).toBe("NoorRattan");
    expect(normalizeGitHubProfileInput("https://www.github.com/NoorRattan/")).toBe("NoorRattan");
  });

  it("uses the owner segment when a repository link is pasted", () => {
    expect(normalizeGitHubProfileInput("https://github.com/NoorRattan/GitRoast.ai")).toBe("NoorRattan");
  });

  it("rejects non-GitHub and invalid profile inputs", () => {
    expect(normalizeGitHubProfileInput("https://gitlab.com/NoorRattan")).toBeNull();
    expect(normalizeGitHubProfileInput("https://github.com/search?q=NoorRattan")).toBeNull();
    expect(normalizeGitHubProfileInput("-bad-name")).toBeNull();
    expect(normalizeGitHubProfileInput("")).toBeNull();
  });
});
