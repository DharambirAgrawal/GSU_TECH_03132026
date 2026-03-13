import FeaturePlaceholder from "../../../components/common/FeaturePlaceholder";

export default function AccuracyPage() {
  return (
    <FeaturePlaceholder
      title="Accuracy"
      description="Accuracy checks, factual error summaries, and correction trends will live in this module."
      endpoint="/api/accuracy/*"
    />
  );
}
