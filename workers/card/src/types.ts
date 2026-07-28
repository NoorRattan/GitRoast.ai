export type Env = {
  BACKEND_BASE_URL: string;
};

export type CardData = {
  username: string;
  schema_version: number;
  percentile_benchmark: number;
  percentile_sample_size: number;
  percentile_cold_start: boolean;
  scores: {
    profile_strength: number;
    project_depth: number;
    commit_consistency: number;
    tech_diversity: number;
    percentile_benchmark: number;
  };
  avatar_url: string | null;
};

export type Fetcher = typeof fetch;

export type RenderDeps = {
  renderSvg?: (data: CardData, avatarDataUri: string) => Promise<string>;
  rasterizeSvg?: (svg: string) => Promise<Uint8Array>;
  fallbackCard?: Uint8Array;
};
