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
    title: "Run the live World Bank Analyst pipeline",
    description:
      "Calls the real backend endpoints and only reports the state the pipeline has actually reached.",
    boundaryLabel: "API-backed status",
    boundaryDetail:
      "Real run uses /pipeline/trigger and /pipeline/status. If the run is queued, slow, or failed, the UI stays truthful.",
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
      "Calls the World Bank Indicators API v2 for six macro series \u2014 GDP growth, inflation, unemployment, current account balance, government debt, and nominal GDP \u2014 across all 17 monitored markets. The 2010\u20132024 window gives the statistical layer 15 annual observations per country to establish a defensible cross-panel baseline. Raw API payloads are archived to GCS before analysis runs.",
    outcome:
      "102 normalised year-on-year records ready for the statistical pass, plus a raw payload archive for provenance.",
    latencyNote:
      "The run pulls six indicators across all 17 markets and normalizes uneven source rows before analysis can start.",
    statusCopy: {
      pending: "Waiting to request the approved World Bank indicator set.",
      running:
        "Pulling the approved World Bank indicator set for the active monitored panel.",
      complete: "World Bank source data was fetched and normalized for this run.",
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
      "Pandas computes year-over-year percentage changes and tests each record against a z-score threshold of 2.0 standard deviations. The threshold is calibrated cross-panel per indicator \u2014 not per country \u2014 because each country has roughly seven annual observations in the target window, too few for a reliable per-country baseline. Pooled across 17 markets, each indicator has ~102 observations. A GDP growth swing that is routine in one regime registers clearly against the full global peer group.",
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
        detail: "Lining up yearly observations across the monitored indicators.",
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
    title: "Country + panel synthesis",
    story:
      "Three model passes per run. Step 1: the model receives one indicator\u2019s signal data per call and returns a structured note \u2014 trend direction, a 2\u20133 sentence narrative, risk level, and confidence. Step 2: all six indicator notes for a country feed a second call that returns an executive summary, top risk flags, economic outlook (bullish / cautious / bearish), and a regime label (recovery / expansion / overheating / contraction / stagnation). Step 3: all 17 country briefings feed a single panel overview call. Every output is validated against a Pydantic schema before being accepted.",
    outcome:
      "17 country briefings and one cross-market panel overview, each with risk flags, regime label, and structured outlook fields.",
    latencyNote:
      "This is the longest stage because the model works through the full 17-country panel before the overview pass can finish.",
    statusCopy: {
      pending: "Waiting for the AI synthesis stage.",
      running:
        "Turning structured signals into country briefings and a global overview. This is the longest stage because the model works through the full 17-country panel.",
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
      "Country briefings, the panel overview, and runtime status are written through a shared repository contract that supports local JSON-backed storage and durable Firestore-backed storage without changing the calling code. The local path keeps development deterministic; Firestore turns on via an environment variable. The same contract is used by the development runner and the deployed Cloud Run job.",
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
      "Claims the single active run slot and hands the bounded pipeline execution to Cloud Run Jobs when the deployment path is live.",
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
        detail: "Verifying Cloud Run job configuration and runtime credentials.",
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
  [...PIPELINE_STAGE_MODEL, ...Object.values(LIVE_ONLY_STAGE_META)].map((stage) => [
    stage.name,
    stage,
  ]),
);

export function buildDefaultPipelineSteps() {
  return PIPELINE_STAGE_MODEL.map((stage) => ({
    name: stage.name,
    status: "pending",
  }));
}

export function getPipelineStageMeta(stepName) {
  return PIPELINE_STAGE_LOOKUP[stepName] || {
    ...FALLBACK_STAGE,
    name: stepName || FALLBACK_STAGE.name,
  };
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
