import { describe, expect, it } from "vitest";
import { normalizeGitHubProfileInput } from "./github-profile";

describe("normalizeGitHubProfileInput", () => {
  it("keeps valid GitHub usernames for existing shared URLs", () => {
    expect(normalizeGitHubProfileInput("octocat")).toBe("octocat");
    expect(normalizeGitHubProfileInput("torvalds")).toBe("torvalds");
  });

  it("extracts usernames from GitHub profile links", () => {
    expect(normalizeGitHubProfileInput("https://github.com/octocat")).toBe("octocat");
    expect(normalizeGitHubProfileInput("github.com/octocat?tab=repositories")).toBe("octocat");
    expect(normalizeGitHubProfileInput("https://www.github.com/octocat/")).toBe("octocat");
  });

  it("uses the owner segment when a repository link is pasted", () => {
    expect(normalizeGitHubProfileInput("https://github.com/octocat/Hello-World")).toBe("octocat");
  });

  it("rejects non-GitHub and invalid profile inputs", () => {
    expect(normalizeGitHubProfileInput("https://gitlab.com/octocat")).toBeNull();
    expect(normalizeGitHubProfileInput("https://github.com/search?q=octocat")).toBeNull();
    expect(normalizeGitHubProfileInput("-bad-name")).toBeNull();
    expect(normalizeGitHubProfileInput("")).toBeNull();
  });
});
