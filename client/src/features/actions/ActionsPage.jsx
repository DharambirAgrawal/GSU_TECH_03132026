import { useState } from "react";

const exampleErrors = [
  {
    type: "AI Blocked",
    message: "Your robots.txt or meta tags are preventing AI and search engines from crawling key pages.",
    suggestion: "Allow AI and search engine bots to access important product and info pages."
  },
  {
    type: "Poor HTML Structure",
    message: "Missing headings, meta tags, or broken schema make it hard for AI and search engines to understand your site.",
    suggestion: "Add semantic HTML, proper headings, and structured data."
  },
  {
    type: "Content Hidden",
    message: "Key product details are only in images or PDFs, not in HTML.",
    suggestion: "Ensure all important info is available as text on the page."
  },
  {
    type: "Technical Errors",
    message: "Some product or checkout pages return 404 or 500 errors.",
    suggestion: "Fix broken links and server errors promptly."
  }
];

const suggestionPDFs = [
  {
    team: "Marketing",
    description: "SEO, AI-readiness, and content best practices.",
    comingSoon: true
  },
  {
    team: "Development",
    description: "Technical SEO, accessibility, and performance checklist.",
    comingSoon: true
  },
  {
    team: "Consumer Behavior",
    description: "UX, analytics, and conversion optimization tips.",
    comingSoon: true
  }
];

export default function ActionsPage() {
  const [downloading, setDownloading] = useState(null);

  return (
    <section className="page-card actions-page">
      <h2>Website Issues Detected</h2>
      <ul className="error-list">
        {exampleErrors.map((err, i) => (
          <li key={i} className="error-item">
            <b>{err.type}:</b> {err.message}
            <div className="error-suggestion">Suggestion: {err.suggestion}</div>
          </li>
        ))}
      </ul>

      <h3 style={{ marginTop: 32 }}>Download Suggestions (PDF)</h3>
      <div className="suggestion-pdf-row">
        {suggestionPDFs.map((pdf, i) => (
          <div key={pdf.team} className="suggestion-pdf-card">
            <div className="pdf-title">{pdf.team} Team</div>
            <div className="pdf-desc">{pdf.description}</div>
            <button className="btn btn-primary" disabled>
              {pdf.comingSoon ? "Coming Soon" : downloading === pdf.team ? "Downloading..." : "Download PDF"}
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}
