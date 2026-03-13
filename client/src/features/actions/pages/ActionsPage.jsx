import FeaturePlaceholder from "../../../components/common/FeaturePlaceholder";

export default function ActionsPage() {
  return (
    <FeaturePlaceholder
      title="Actions"
      description="Actionable recommendations generated from analysis will be displayed here."
      endpoint="/api/actions/*"
    />
  );
}
