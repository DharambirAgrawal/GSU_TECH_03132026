import React from "react";

const mockData = {
  totalMentions: 124,
  platforms: [
    { name: "ChatGPT", mentions: 60 },
    { name: "Gemini", mentions: 40 },
    { name: "Claude", mentions: 24 },
  ],
  sentiment: {
    positive: 70,
    neutral: 40,
    negative: 14,
  },
  recentMentions: [
    {
      platform: "ChatGPT",
      text: "Vigil is a leading solution for AI visibility.",
      date: "2026-03-10",
      sentiment: "positive",
    },
    {
      platform: "Gemini",
      text: "The company Vigil was referenced in the context of compliance.",
      date: "2026-03-09",
      sentiment: "neutral",
    },
    {
      platform: "Claude",
      text: "Some users reported issues with Vigil's dashboard.",
      date: "2026-03-08",
      sentiment: "negative",
    },
  ],
};

export default function VisibilityPage() {
  const { totalMentions, platforms, sentiment, recentMentions } = mockData;
  const sentimentTotal = sentiment.positive + sentiment.neutral + sentiment.negative;

  return (
    <main className="dashboard-main visibility-dashboard">
      <header className="dashboard-header">
        <h1>Company Visibility</h1>
        <p className="dashboard-subtitle">How your company is mentioned by AI platforms</p>
      </header>
      <section className="dashboard-section stats-section">
        <div className="stat-card">
          <h2>Total Mentions</h2>
          <div className="stat-value">{totalMentions}</div>
        </div>
        <div className="stat-card">
          <h2>Sentiment</h2>
          <div className="sentiment-bar">
            <div style={{width: `${(sentiment.positive/sentimentTotal)*100}%`, background: '#4caf50'}} title="Positive" />
            <div style={{width: `${(sentiment.neutral/sentimentTotal)*100}%`, background: '#ffc107'}} title="Neutral" />
            <div style={{width: `${(sentiment.negative/sentimentTotal)*100}%`, background: '#f44336'}} title="Negative" />
          </div>
          <div className="sentiment-labels">
            <span> {sentiment.positive}</span>
            <span> {sentiment.neutral}</span>
            <span> {sentiment.negative}</span>
          </div>
        </div>
      </section>
      <section className="dashboard-section platform-section">
        <h2>Mentions by Platform</h2>
        <table className="platform-table">
          <thead>
            <tr>
              <th>Platform</th>
              <th>Mentions</th>
            </tr>
          </thead>
          <tbody>
            {platforms.map(p => (
              <tr key={p.name}>
                <td>{p.name}</td>
                <td>{p.mentions}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section className="dashboard-section recent-section">
        <h2>Recent Mentions</h2>
        <ul className="recent-mentions-list">
          {recentMentions.map((m, i) => (
            <li key={i} className={`mention-item ${m.sentiment}`}>
              <div className="mention-header">
                <span className="mention-platform">{m.platform}</span>
                <span className="mention-date">{m.date}</span>
                <span className="mention-sentiment">{m.sentiment}</span>
              </div>
              <div className="mention-text">{m.text}</div>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
