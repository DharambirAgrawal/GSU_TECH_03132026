import { useState, useEffect } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from './assets/vite.svg'
import logoImg from './assets/logo.png'
import { House } from 'lucide-react';
import './App.css'

function App() {
  const [count, setCount] = useState(0)
  const [username, setUsername] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [page, setPage] = useState("login");
  const [newUser, setNewUser] = useState(false);
  const [companyName, setCompanyName] = useState("");
  const [companyDetails, setCompanyDetails] = useState("");
  const [activeTab, setActiveTab] = useState("Dashboard");
  const [selectedProduct, setSelectedProduct] = useState("Laptops");
  const [customProduct, setCustomProduct] = useState("");
  const [showCustomInput, setShowCustomInput] = useState(false);
  const productOptions = ["Laptops", "Tablets", "Cell phones", "Custom..."];

  useEffect(() => {
    const savedUser = localStorage.getItem("rememberedUser");

    if (savedUser) {
      setUsername(savedUser);
      setRememberMe(true);
    }
  }, []);

  const handleLoginSubmit = (e) => {
    e.preventDefault();
    if (rememberMe) {
      localStorage.setItem("rememberedUser", username);
    } else {
      localStorage.removeItem("rememberedUser");
    }
    setPage("dashboard");
  };
  
  const handleRegisterSubmit = (e) => {
    e.preventDefault();
    alert(`Confirmation email sent to ${username} for company: ${companyName}`);
    setNewUser(false);
    setCompanyName("");
    setCompanyDetails("");
    setUsername("");
  }


  return (
    <>
      {page === "login" ? (
        <section id="center">
          <div className="logo">
            {/* <img src={heroImg} className="base" width="170" height="179" alt="" />
            <img src={reactLogo} className="framework" alt="React logo" />
            <img src={viteLogo} className="vite" alt="Vite logo" /> */}
          </div>
          <form className="signin-form" onSubmit={newUser ? handleRegisterSubmit : handleLoginSubmit}>
            <h2>{newUser ? "Register Below" : "Sign In"}</h2>
            <input
              type="user"
              placeholder="Enter username"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
            />
            
            {newUser && (
              <>
                <input
                  type="text"
                  placeholder="Company Name"
                  value={companyName}
                  onChange={e => setCompanyName(e.target.value)}
                  required
                />
                <textarea
                  placeholder="Company Details"
                  value={companyDetails}
                  onChange={e => setCompanyDetails(e.target.value)}
                  required
                  rows={3}
                  style={{resize: 'vertical', marginBottom: '1rem'}}
                />
              </>
            )}
            <div className="form-options">
              <label className="remember-me">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={e => setRememberMe(e.target.checked)}
                  disabled={newUser}
                />
                Remember me
              </label>
              <button
                type="button"
                className="newuser-link"
                onClick={() => setNewUser(!newUser)}
                style={{marginLeft: '1rem'}}
              >
                {newUser ? "Back to Sign In" : "New user? Click here"}
              </button>
            </div>
            <button type="submit">{newUser ? "Register" : "Login"}</button>
          </form>
        </section>
      ) : (
        <div className="dashboard-layout">
          <aside className="sidebar">
            <h1 style={{textAlign: 'center', margin: '2rem 0 1rem 0', fontSize: '2.2rem', letterSpacing: 2}}> Vigil </h1>
            {/* <h3 className="sidebar-title">Analytics</h3> */}
            <nav>
              <ul className="sidebar-tabs">
                {['Dashboard', 'Visibility', 'Accuracy', 'Competitors', 'Error Log'].map(tab => (
                  <li key={tab} className={activeTab === tab ? 'active' : ''}>
                    <button onClick={() => setActiveTab(tab)}>
                      {tab === 'Dashboard' && <House size={18} style={{marginRight: 8, verticalAlign: 'middle'}} />}
                      {tab}
                      
                    </button>
                  </li>
                ))}
              </ul>
            </nav>
          </aside>
          <main className="dashboard-main">
            <header className="dashboard-header">
              <div className="dashboard-actions">
                <button className="history-btn" onClick={() => setPage("history")}>History</button>
                <button
                  className="generate-btn"
                  disabled={!(showCustomInput ? customProduct.trim() : selectedProduct)}
                  onClick={() => {/* handle generate logic here */}}
                >
                  Generate
                </button>
                <select
                  className="product-dropdown"
                  value={showCustomInput ? "Custom..." : selectedProduct}
                  onChange={e => {
                    if (e.target.value === "Custom...") {
                      setShowCustomInput(true);
                      setSelectedProduct("");
                    } else {
                      setShowCustomInput(false);
                      setSelectedProduct(e.target.value);
                    }
                  }}
                >
                  {productOptions.map(option => (
                    <option key={option} value={option}>{option}</option>
                  ))}
                </select>
                {showCustomInput && (
                  <input
                    className="custom-product-input"
                    type="text"
                    placeholder="Enter product name"
                    value={customProduct}
                    onChange={e => setCustomProduct(e.target.value)}
                    style={{marginLeft: 8, minWidth: 120}}
                  />
                )}
                <button className="signout-btn" onClick={() => setPage("login")}>Sign out</button>
              </div>
            </header>
            <section className="dashboard-content">
              {activeTab === 'Dashboard' && (
                <>
                  <h1>Welcome to your dashboard!</h1>
                </>
              )}
              {activeTab === 'Visibility' && (
                <>
                  <h1>Profile</h1>
                  <p>Username: {username}</p>
                  {companyName && <p>Company: {companyName}</p>}
                  {companyDetails && <p>Details: {companyDetails}</p>}
                </>
              )}
              {activeTab === 'Competitors' && (
                <>
                  <h1>asdf</h1>
                  <p>Username: {username}</p>
                </>
              )}
              {activeTab === 'Accuracy' && (
                <>
                  <h1>Settings</h1>
                  <p>Settings content goes here.</p>
                </>
              )}
            </section>
          </main>
        </div>
      )}
      {page === "history" && (
        <section className="history-page">
          <h2>History</h2>
          <button onClick={() => setPage("dashboard")}>Back to Dashboard</button>
          {/* Add your history content here */}
        </section>
      )}
    </>
  )
}

export default App
