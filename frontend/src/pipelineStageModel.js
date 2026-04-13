const FALLBACK_STAGE = {
  name: "processing",
  title: "Processing",
  story: "Working through the current pipeline stage.",
  outcome: "The run is still moving through the active step.",
  latencyNote: "This stage is still working through the current run.",
  statusCopy: {
    pending: "Waiting for the next execution step.",
    running: "Working through the current pipeline stage.",
    complete: "This pipeline stage completed.",
    failed: "The run stopped in the current pipeline stage.",
  },
  activities: [
    {
      label: "Processing",
      verb: "processing",
      detail: "Working through the current pipeline stage.",
    },
  ],
  demoDurationMs: 700,
};

export const PIPELINE_TRIGGER_MODES = [
  {
    key: "real",
    label: "Real run",
    eyebrow: "Truthful runtime",
    title: "Run the configured World Analyst pipeline",
    description:
      "Calls the real backend endpoints and only reports the state the configured runtime has actually reached.",
    boundaryLabel: "API-backed status",
    boundaryDetail:
      "Real run uses /pipeline/trigger and /pipeline/status. In live deployment that means the full monitored panel; in local mode it stays on the deterministic development slice.",
    actionLabel: "Run pipeline",
    replayLabel: "Pipeline running",
    tone: "success",
  },
  {
    key: "demo",
    label: "Demo walkthrough",
    eyebrow: "Frontend-only simulation",
    title: "Replay the product story without mutating backend state",
    description:
      "Animates through the shared pipeline stage model in the browser so you can explain the flow quickly without writing fake status records.",
    boundaryLabel: "Browser-only replay",
    boundaryDetail:
      "Demo walkthrough never calls the trigger endpoint, never writes simulated status, and never unlocks country detail by itself.",
    actionLabel: "Replay walkthrough",
    replayLabel: "Replay walkthrough",
    tone: "warning",
  },
];

export const PIPELINE_STAGE_MODEL = [
  {
    name: "fetch",
    title: "Fetch and normalize",
    story:
      "Fetches the approved indicator scope for the current runtime. In live mode that means **six macro indicators** across the **17-market monitored panel**; in local mode it stays on the deterministic development slice. Raw payloads are archived for provenance.",
    outcome:
      "Normalized year-on-year records ready for the statistical pass, plus raw payload provenance for follow-up.",
    latencyNote:
      "The run fetches the approved indicator scope for the current runtime and normalizes uneven source rows before analysis starts.",
    statusCopy: {
      pending: "Waiting to request the approved World Bank indicator scope.",
      running:
        "Requesting and normalizing the approved World Bank indicator scope for the current runtime.",
      complete:
        "World Bank source data was fetched and normalized for this run.",
      failed:
        "The run stopped while requesting or normalizing World Bank source data.",
    },
    activities: [
      {
        label: "Open source",
        verb: "opening",
        detail:
          "Connecting to the World Bank Indicators API for the approved panel.",
      },
      {
        label: "Collect series",
        verb: "pulling",
        detail: "Fetching GDP, inflation, labour, fiscal, and external series.",
      },
      {
        label: "Normalize rows",
        verb: "shaping",
        detail: "Normalizing raw indicator payloads into one comparable frame.",
      },
      {
        label: "Seal ingest",
        verb: "indexing",
        detail: "Finalizing the source ingest before the signal pass starts.",
      },
    ],
    demoDurationMs: 900,
  },
  {
    name: "analyse",
    title: "Statistical signal layer",
    story:
      "Pandas scores year-over-year changes against a **2.0 standard deviation anomaly threshold**. In live mode that context comes from the full monitored panel; in local mode it reflects the deterministic development slice.",
    outcome:
      "Structured signal layer: deltas, z-scores, anomaly flags, and regime context. The model never touches raw numbers.",
    latencyNote:
      "The run aligns yearly histories across indicators first so the model receives resolved maths instead of raw source noise.",
    statusCopy: {
      pending: "Waiting for the statistical analysis stage.",
      running:
        "Calculating deltas, stress direction, anomaly flags, and regime context with Pandas.",
      complete: "Pandas finished the statistical pass for this run.",
      failed: "The run stopped while computing the statistical signal layer.",
    },
    activities: [
      {
        label: "Frame data",
        verb: "assembling",
        detail:
          "Lining up yearly observations across the monitored indicators.",
      },
      {
        label: "Score change",
        verb: "measuring",
        detail: "Calculating deltas, direction of travel, and stress movement.",
      },
      {
        label: "Flag anomalies",
        verb: "screening",
        detail: "Testing each indicator against anomaly thresholds.",
      },
      {
        label: "Package signals",
        verb: "staging",
        detail: "Preparing the structured signal layer for model input.",
      },
    ],
    demoDurationMs: 1000,
  },
  {
    name: "synthesise",
    title: "Country + overview synthesis",
    story:
      "The LLM turns the signal layer into **country briefings**, **regime labels**, **risk flags**, and one overview for the stored slice. Live mode works through the full monitored panel; local mode stays on the deterministic development slice. Every output must pass **Pydantic schema validation**.",
    outcome:
      "Country briefings plus one overview record, each with risk flags, regime label, and structured outlook fields.",
    latencyNote:
      "This is usually the longest stage because the model works through every country in the current runtime scope before the overview pass can finish.",
    statusCopy: {
      pending: "Waiting for the AI synthesis stage.",
      running:
        "Turning structured signals into country briefings and an overview for the current runtime scope.",
      complete:
        "Country narratives and the global overview were generated for this run.",
      failed: "The run stopped while generating the analyst narratives.",
    },
    activities: [
      {
        label: "Prepare context",
        verb: "aligning",
        detail: "Gathering structured indicator evidence for the model.",
      },
      {
        label: "Write notes",
        verb: "drafting",
        detail: "Turning each indicator into analyst-ready signal notes.",
      },
      {
        label: "Blend signals",
        verb: "weaving",
        detail: "Combining risk signals into country-level narratives.",
      },
      {
        label: "Work queue",
        verb: "orchestrating",
        detail: "Moving through the monitored-set country briefing queue.",
      },
      {
        label: "Compare markets",
        verb: "reconciling",
        detail: "Comparing cross-market pressure before the overview pass.",
      },
      {
        label: "Finish overview",
        verb: "composing",
        detail: "Writing the monitored-set overview and risk language.",
      },
      {
        label: "Check schema",
        verb: "validating",
        detail: "Verifying structured output before persistence.",
      },
    ],
    demoDurationMs: 1400,
  },
  {
    name: "store",
    title: "Persist outputs",
    story:
      "Country briefings, the overview, and run metadata are committed through a **shared repository layer** supporting local in-memory storage or remote **Firestore**. Run completion metrics are sealed into a durable **status contract**.",
    outcome:
      "Dashboard-ready records in the configured store. Pipeline status sealed with per-step durations and completion timestamps.",
    latencyNote:
      "The final stage seals the records that power the dashboard and the status contract the frontend reads back.",
    statusCopy: {
      pending: "Waiting to persist the finished briefing.",
      running:
        "Writing processed insights, the monitored-set overview, and runtime status to the configured store.",
      complete:
        "Processed insights, the monitored-set overview, and status were saved for this run.",
      failed: "The run stopped while persisting the finished outputs.",
    },
    activities: [
      {
        label: "Prepare records",
        verb: "packaging",
        detail: "Preparing processed insight, overview, and status payloads.",
      },
      {
        label: "Write insights",
        verb: "committing",
        detail: "Writing country and panel records to the repository.",
      },
      {
        label: "Archive raw",
        verb: "archiving",
        detail: "Recording raw payload provenance for follow-up.",
      },
      {
        label: "Seal run",
        verb: "closing",
        detail: "Finalizing the durable pipeline status contract.",
      },
    ],
    demoDurationMs: 800,
  },
];

const LIVE_ONLY_STAGE_META = {
  dispatch: {
    name: "dispatch",
    title: "Dispatch Cloud Run job",
    story:
      "Validates configuration constraints and claims the **exclusive execution lock** before routing execution instructions safely out to **Google Cloud Run**.",
    outcome: "One accepted background run in the deploy topology.",
    latencyNote:
      "Dispatch must verify runtime configuration and claim the monitored-set run slot before the actual data stages can start.",
    statusCopy: {
      pending: "Waiting for a Cloud Run Job dispatch request.",
      running: "Sending the job to Cloud Run.",
      complete: "Cloud Run accepted the job dispatch request.",
      failed:
        "The run stopped before pipeline execution because Cloud Run dispatch failed.",
    },
    activities: [
      {
        label: "Validate config",
        verb: "checking",
        detail:
          "Verifying Cloud Run job configuration and runtime credentials.",
      },
      {
        label: "Reserve slot",
        verb: "claiming",
        detail:
          "Holding the monitored-set run slot so only one execution stays active.",
      },
      {
        label: "Dispatch job",
        verb: "launching",
        detail: "Handing the bounded panel run to Cloud Run Jobs.",
      },
    ],
    demoDurationMs: 600,
  },
};

const PIPELINE_STAGE_LOOKUP = Object.fromEntries(
  [...PIPELINE_STAGE_MODEL, ...Object.values(LIVE_ONLY_STAGE_META)].map(
    (stage) => [stage.name, stage],
  ),
);

export function buildDefaultPipelineSteps() {
  return PIPELINE_STAGE_MODEL.map((stage) => ({
    name: stage.name,
    status: "pending",
  }));
}

export function getPipelineStageMeta(stepName) {
  return (
    PIPELINE_STAGE_LOOKUP[stepName] || {
      ...FALLBACK_STAGE,
      name: stepName || FALLBACK_STAGE.name,
    }
  );
}

export function getPipelineStageActivities(stepName) {
  return getPipelineStageMeta(stepName).activities;
}

export function getActivePipelineStageActivity(stepName, tick) {
  const activities = getPipelineStageActivities(stepName);
  return activities[tick % activities.length];
}

export function getPipelineStageStatusCopy(stepName, status) {
  return (
    getPipelineStageMeta(stepName).statusCopy[status] ||
    FALLBACK_STAGE.statusCopy.pending
  );
}

export function decoratePipelineSteps(steps) {
  return (steps?.length ? steps : buildDefaultPipelineSteps()).map((step) => ({
    ...getPipelineStageMeta(step.name),
    ...step,
  }));
}
