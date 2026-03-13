import FeaturePlaceholder from "../../../components/common/FeaturePlaceholder";

export default function CrawlPage() {
  return (
    <FeaturePlaceholder
      title="Crawl"
      description="Crawl status, source coverage, and freshness controls will be implemented here."
      endpoint="/api/crawl/*"
    />
  );
}
