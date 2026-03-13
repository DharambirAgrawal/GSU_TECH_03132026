import FeaturePlaceholder from "../../../components/common/FeaturePlaceholder";

export default function RunsPage() {
  return (
    <FeaturePlaceholder
      title="Runs"
      description="This area will support prompt generation, query editing, run start, status polling, and run history views."
      endpoint="/api/runs/*"
    />
  );
}
