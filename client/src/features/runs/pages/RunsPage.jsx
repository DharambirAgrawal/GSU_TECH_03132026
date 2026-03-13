import { useState } from "react";

export default function RunsPage() {
  // Example dropdown options (can be replaced with backend data)
  const initialOptions = [
    { label: "Laptops", value: "Laptops" },
    { label: "Tablets", value: "Tablets" },
    { label: "Cars", value: "Cars" },
    { label: "Other (enter manually)", value: "custom" },
  ];
  const [searchOptions, setSearchOptions] = useState(initialOptions);
  const [selectedOption, setSelectedOption] = useState("");
  const [customInput, setCustomInput] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    setLoading(true);
    setResult(null);
    setTimeout(() => {
      setLoading(false);
      // Simulate backend response with formatted message
      setResult(
        `<div style='text-align:center;'>\n` +
        `<h2 style='color:#7f9cf5;'>No data found</h2>\n` +
        `<p>We couldn't find information on <b>${selectedOption === 'custom' ? customInput : selectedOption}</b>.</p>\n` +
        `<p>Specs on :</p>\n` +
        `<ul style='text-align:left;display:inline-block;'>\n` +
        `<li>Insufficient demand or market interest</li>\n` +
        `<li>Supply chain or inventory issues</li>\n` +
        `<li>Product discontinued or not yet launched</li>\n` +
        `<li>Awaiting approval or compliance checks</li>\n` +
        `<li>Other business or technical constraints</li>\n` +
        `</ul>\n` +
        `<p style='color:#b3b8d4;'>Please check back later or try another product.</p>\n` +
        `</div>`
      );
    }, 1200);
  };

  return (
    <main >
      <h1 style={{ fontWeight: 700, fontSize: 32, marginBottom: 16, letterSpacing: 1, color: '#7f9cf5', textAlign: 'center' }}>Console Runner</h1>
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'flex-end', gap: 16, marginBottom: 32, flexWrap: 'wrap' }}>
        <div>
          <label htmlFor="product-select" style={{ color: '#b3b8d4', fontWeight: 500 }}>Select product:</label><br />
          <select
            id="product-select"
            value={selectedOption}
            onChange={e => setSelectedOption(e.target.value)}
            style={{
              padding: '10px 16px',
              borderRadius: 8,
              border: '1px solid #444',
              background: '#23263a',
              color: '#e0e6f8',
              fontSize: 16,
              minWidth: 180,
              marginTop: 4
            }}
          >
            <option value="" disabled>Select function</option>
            {searchOptions.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
        {selectedOption === 'custom' && (
          <div>
            <label htmlFor="custom-input" style={{  fontWeight: 500 }}>Enter product:</label><br />
            <input
              id="custom-input"
              type="text"
              value={customInput}
              onChange={e => setCustomInput(e.target.value)}
              placeholder="Type product name"
              style={{
                padding: '10px 16px',
                borderRadius: 8,
                border: '1px solid #444',
                background: '#23263a',
                color: '#e0e6f8',
                fontSize: 16,
                minWidth: 180,
                marginTop: 4
              }}
            />
          </div>
        )}
        <button
          onClick={handleSearch}
          disabled={(!selectedOption || (selectedOption === 'custom' && !customInput)) || loading}
          style={{
            padding: '10px 24px',
            borderRadius: 8,
            background: '#7f9cf5',
            color: '#181c2f',
            fontWeight: 600,
            border: 'none',
            fontSize: 16,
            cursor: (!selectedOption || (selectedOption === 'custom' && !customInput) || loading) ? 'not-allowed' : 'pointer',
            boxShadow: '0 2px 8px rgba(127,156,245,0.15)',
            marginTop: 4
          }}
        >
          {loading ? 'Searching...' : 'Search'}
        </button>
      </div>
      <div style={{ minHeight: 120, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        {loading && (
          <div style={{ textAlign: 'center', width: '100%' }}>
            <div className="spinner" style={{ margin: '0 auto', width: 48, height: 48, border: '6px solid #23263a', borderTop: '6px solid #7f9cf5', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
            <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
            <p style={{ color: '#b3b8d4', marginTop: 16 }}>Loading...</p>
          </div>
        )}
        {!loading && result && (
          <div style={{ width: '100%' }} dangerouslySetInnerHTML={{ __html: result }} />
        )}
      </div>
    </main>
  );
}
