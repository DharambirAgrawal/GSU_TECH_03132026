export default function FeaturePlaceholder({ title, description, endpoint }) {
  return (
    <section className="page-card">
      <h2>{title}</h2>
      <p>{description}</p>
      <div className="endpoint-tag">Backend route: {endpoint}</div>
    </section>
  );
}
