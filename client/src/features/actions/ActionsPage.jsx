import FeaturePlaceholder from "../../components/common/FeaturePlaceholder";

export default function ActionsPage() {
  return (
    <FeaturePlaceholder
      title="Actions"
      description="Crawl status, source coverage, and freshness controls will be implemented here."
      endpoint="/api/actions/*"
    />
  );
}
