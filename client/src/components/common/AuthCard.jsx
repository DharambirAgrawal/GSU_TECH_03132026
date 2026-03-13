export default function AuthCard({ title, subtitle, children }) {
  return (
    <main className="auth-shell">
      <section className="auth-card">
        <p className="home-pill">Vigil</p>
        <h1>{title}</h1>
        {subtitle ? <p className="subtitle">{subtitle}</p> : null}
        {children}
      </section>
    </main>
  );
}
