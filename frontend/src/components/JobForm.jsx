import { useState } from "react";
import { Wallet, MapPin, Clock, GraduationCap, Building2, FileSearch, Link2, Sparkles } from "lucide-react";
import { scrapeJobUrl } from "../services/api";

function JobForm({ onAnalyze, loading }) {
  const [jobUrl, setJobUrl] = useState("");
  const [scraping, setScraping] = useState(false);
  const [scrapeError, setScrapeError] = useState("");
  const [scrapeSuccess, setScrapeSuccess] = useState(false);

  const [formData, setFormData] = useState({
    title: "",
    company_profile: "",
    description: "",
    requirements: "",
    benefits: "",
    salary_range: "",
    has_company_logo: 0,
    has_questions: 0,
    location: "",
    employment_type: "",
    required_experience: "",
    required_education: "",
  });

  function handleChange(event) {
    const { name, value, type, checked } = event.target;

    setFormData({
      ...formData,
      [name]: type === "checkbox" ? (checked ? 1 : 0) : value,
    });
  }

  async function handleScrapeUrl(event) {
    if (event) event.preventDefault();
    if (!jobUrl.trim()) return;

    let cleanUrl = jobUrl.trim();
    if (!/^https?:\/\//i.test(cleanUrl)) {
      cleanUrl = "https://" + cleanUrl;
      setJobUrl(cleanUrl);
    }

    setScraping(true);
    setScrapeError("");
    setScrapeSuccess(false);

    try {
      const data = await scrapeJobUrl(cleanUrl);
      
      const hasContent = Boolean(
        data.title || data.company || data.company_profile || data.description || data.location
      );

      setFormData((prev) => ({
        ...prev,
        title: data.title || prev.title,
        company_profile: data.company_profile || data.company || prev.company_profile,
        description: data.description || prev.description,
        requirements: data.requirements || prev.requirements,
        benefits: data.benefits || prev.benefits,
        salary_range: data.salary_range || data.salary || prev.salary_range,
        location: data.location || prev.location,
        employment_type: data.employment_type || prev.employment_type,
        required_experience: data.required_experience || prev.required_experience,
        required_education: data.required_education || prev.required_education,
        has_company_logo: data.has_company_logo !== undefined ? data.has_company_logo : prev.has_company_logo,
        has_questions: data.has_questions !== undefined ? data.has_questions : prev.has_questions,
      }));

      if (hasContent) {
        setScrapeSuccess(true);
      } else {
        setScrapeError("Could not automatically extract job details from this link. Please fill in the details below.");
      }
    } catch (err) {
      setScrapeError(err.message || "Failed to fetch details from this URL.");
    } finally {
      setScraping(false);
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    onAnalyze(formData);
  }

  return (
    <form className="job-form" onSubmit={handleSubmit}>
      <fieldset className="url-scrape-section">
        <legend style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Link2 size={16} /> Import from Job Link
        </legend>
        <div className="field">
          <label>Paste Job Link (LinkedIn, Indeed, Glassdoor, etc.)</label>
          <div style={{ display: 'flex', gap: '8px' }}>
            <input
              type="text"
              inputMode="url"
              value={jobUrl}
              onChange={(e) => setJobUrl(e.target.value)}
              placeholder="https://www.linkedin.com/jobs/view/..."
              disabled={scraping}
              style={{ flex: 1 }}
            />
            <button
              type="button"
              className="submit-btn"
              onClick={handleScrapeUrl}
              disabled={scraping || !jobUrl.trim()}
              style={{
                width: 'auto',
                padding: '0 16px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                marginTop: 0,
                fontSize: '0.9rem'
              }}
            >
              <Sparkles size={16} />
              {scraping ? "Fetching…" : "Auto-Fill"}
            </button>
          </div>
          {scrapeError && (
            <span style={{ color: "#ef4444", fontSize: "0.85rem", marginTop: "6px", display: "block" }}>
              {scrapeError}
            </span>
          )}
          {scrapeSuccess && (
            <span style={{ color: "#22c55e", fontSize: "0.85rem", marginTop: "6px", display: "block" }}>
              ✓ Form fields populated successfully from link!
            </span>
          )}
        </div>
      </fieldset>

      <fieldset>
        <legend>Position</legend>
        <div className="field">
          <label>Job title</label>
          <input
            type="text"
            name="title"
            value={formData.title}
            onChange={handleChange}
            placeholder="e.g. Python Developer"
          />
        </div>
      </fieldset>

      <fieldset>
        <legend>Content</legend>

        <div className="field">
          <label>Company profile</label>
          <textarea
            name="company_profile"
            value={formData.company_profile}
            onChange={handleChange}
            placeholder="What does the company say about itself?"
            rows={3}
          />
        </div>

        <div className="field">
          <label>Job description</label>
          <textarea
            name="description"
            value={formData.description}
            onChange={handleChange}
            placeholder="Paste the full job description here"
            rows={6}
            required
          />
        </div>

        <div className="field">
          <label>Requirements</label>
          <textarea
            name="requirements"
            value={formData.requirements}
            onChange={handleChange}
            placeholder="Required skills and qualifications"
            rows={3}
          />
        </div>

        <div className="field">
          <label>Benefits</label>
          <textarea
            name="benefits"
            value={formData.benefits}
            onChange={handleChange}
            placeholder="Salary, benefits, perks mentioned"
            rows={3}
          />
        </div>
      </fieldset>

      <fieldset>
        <legend>Compensation &amp; location</legend>
        <div className="row-2">
          <div className="field">
            <label>Salary range</label>
            <div className="input-icon-row">
              <Wallet size={15} strokeWidth={1.8} />
              <input
                type="text"
                name="salary_range"
                value={formData.salary_range}
                onChange={handleChange}
                placeholder="$80,000–$120,000"
              />
            </div>
          </div>

          <div className="field">
            <label>Location</label>
            <div className="input-icon-row">
              <MapPin size={15} strokeWidth={1.8} />
              <input
                type="text"
                name="location"
                value={formData.location}
                onChange={handleChange}
                placeholder="New York, NY"
              />
            </div>
          </div>
        </div>
      </fieldset>

      <fieldset>
        <legend>Employment</legend>
        <div className="row-2">
          <div className="field">
            <label>Employment type</label>
            <select name="employment_type" value={formData.employment_type} onChange={handleChange}>
              <option value="">Select</option>
              <option value="Full-time">Full-time</option>
              <option value="Part-time">Part-time</option>
              <option value="Contract">Contract</option>
              <option value="Internship">Internship</option>
            </select>
          </div>

          <div className="field">
            <label>Required experience</label>
            <div className="input-icon-row">
              <Clock size={15} strokeWidth={1.8} />
              <input
                type="text"
                name="required_experience"
                value={formData.required_experience}
                onChange={handleChange}
                placeholder="2+ years"
              />
            </div>
          </div>
        </div>

        <div className="field">
          <label>Required education</label>
          <div className="input-icon-row">
            <GraduationCap size={15} strokeWidth={1.8} />
            <input
              type="text"
              name="required_education"
              value={formData.required_education}
              onChange={handleChange}
              placeholder="Bachelor's degree"
            />
          </div>
        </div>
      </fieldset>

      <fieldset>
        <legend>Listing signals</legend>
        <div className="checkbox-grid">
          <label className="checkbox-card">
            <input
              type="checkbox"
              name="has_company_logo"
              checked={formData.has_company_logo === 1}
              onChange={handleChange}
            />
            <Building2 size={16} strokeWidth={1.8} color="var(--muted)" />
            Company has a logo
          </label>

          <label className="checkbox-card">
            <input
              type="checkbox"
              name="has_questions"
              checked={formData.has_questions === 1}
              onChange={handleChange}
            />
            <FileSearch size={16} strokeWidth={1.8} color="var(--muted)" />
            Screening questions included
          </label>
        </div>
      </fieldset>

      <button type="submit" className="submit-btn" disabled={loading}>
        {loading ? "Reviewing…" : "Run review"}
      </button>
    </form>
  );
}

export default JobForm;