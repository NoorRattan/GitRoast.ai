import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "GitRoast.ai",
    short_name: "GitRoast",
    description: "Transparent GitHub profile audits with local roasts and improvement roadmaps.",
    start_url: "/",
    display: "standalone",
    background_color: "#101111",
    theme_color: "#101111",
    icons: [
      {
        src: "/icon.svg",
        sizes: "any",
        type: "image/svg+xml"
      }
    ]
  };
}
