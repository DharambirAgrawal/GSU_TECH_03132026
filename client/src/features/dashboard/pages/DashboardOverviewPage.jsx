import { useOutletContext } from "react-router-dom";

export default function DashboardOverviewPage() {
  const { profile } = useOutletContext();

  return (
    <section className="stats-grid">
      <article className="stat">
        <h3>Company Domain</h3>
        <p>{profile?.company?.approved_email_domain || "-"}</p>
      </article>
      <article className="stat">
        <h3>Role</h3>
        <p>{profile?.user?.role || "member"}</p>
      </article>
      <article className="stat">
        <h3>Visibility Score</h3>
        <p>{profile?.company?.ai_visibility_score ?? 0}</p>
      </article>
      <article className="stat">
        <h3>Accuracy Score</h3>
        <p>{profile?.company?.accuracy_score ?? 0}</p>
      </article>
    </section>
  );
}
