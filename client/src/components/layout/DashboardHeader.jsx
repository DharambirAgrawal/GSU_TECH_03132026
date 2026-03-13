import { useEffect, useMemo, useRef, useState } from "react";
import {
	CalendarClock,
	CheckCircle2,
	ClipboardList,
	PlayCircle,
	Sparkles,
	WandSparkles,
	X,
} from "lucide-react";

import {
	formatDateTime,
	formatRelativeTime,
	formatInteger,
} from "../../features/dashboard/analyticsUtils";

export default function DashboardHeader({
	profile,
	analytics,
	onGenerate,
	onStartDraft,
	onCancelDraft,
	hasDraft,
	draft,
}) {
	const PRODUCT_PRESETS = [6, 10, 20, 40];
	const companyName = profile?.company?.name || "Dashboard";
	const approvedDomain = profile?.company?.approved_email_domain || "No approved domain";
	const userRole = profile?.user?.role || "member";
	const primaryInputRef = useRef(null);
	const [isModalOpen, setIsModalOpen] = useState(false);
	const [isSubmitting, setIsSubmitting] = useState(false);
	const [error, setError] = useState("");
	const [successMessage, setSuccessMessage] = useState("");
	const [form, setForm] = useState({
		product_specification: "",
		additional_detail: "",
		n_iteration: 10,
	});

	const draftPromptCount = draft?.prompts?.length || 0;
	const lastSimulationTimestamp =
		analytics?.summary?.last_simulation_completed_at ||
		analytics?.activity?.[0]?.timestamp ||
		null;
	const lastSimulationStatus = analytics?.summary?.last_simulation_status || null;
	const hasBackendSimulation = Boolean(lastSimulationTimestamp || lastSimulationStatus);
	const lastSimulationLabel = lastSimulationTimestamp
		? formatDateTime(lastSimulationTimestamp)
		: lastSimulationStatus
			? `Status: ${lastSimulationStatus}`
			: "No simulation yet";
	const lastSimulationRelative = lastSimulationTimestamp
		? formatRelativeTime(lastSimulationTimestamp)
		: hasBackendSimulation
			? "Simulation data synced from analytics"
			: "Ready for your first run";
	const simulationChecklist = useMemo(
		() => [
			`Company scope: ${companyName}`,
			`Approved domain: ${approvedDomain}`,
			`Prompt volume: ${formatInteger(form.n_iteration)} queries`,
		],
		[approvedDomain, companyName, form.n_iteration]
	);
	const isReviewMode = hasDraft && draft?.prompts?.length;
	const trimmedProductSpec = form.product_specification.trim();
	const detailLength = form.additional_detail.trim().length;
	const canGenerate = Boolean(trimmedProductSpec) && Number(form.n_iteration) >= 1 && Number(form.n_iteration) <= 100;

	useEffect(() => {
		if (!isModalOpen) {
			return undefined;
		}

		const previousOverflow = document.body.style.overflow;
		document.body.style.overflow = "hidden";

		const handleKeyDown = (event) => {
			if (event.key === "Escape" && !isSubmitting) {
				setIsModalOpen(false);
			}
		};

		window.addEventListener("keydown", handleKeyDown);
		window.setTimeout(() => {
			primaryInputRef.current?.focus();
		}, 20);

		return () => {
			document.body.style.overflow = previousOverflow;
			window.removeEventListener("keydown", handleKeyDown);
		};
	}, [isModalOpen, isSubmitting, isReviewMode]);

	const openModal = () => {
		setError("");
		setSuccessMessage("");
		setIsModalOpen(true);
	};

	const closeModal = () => {
		if (isSubmitting) return;
		setError("");
		setSuccessMessage("");
		setIsModalOpen(false);
	};

	const updateField = (event) => {
		const { name, value } = event.target;
		setForm((prev) => ({ 
			...prev, 
			[name]: name === "n_iteration" ? value : value 
		}));
	};

	const handleGenerate = async (event) => {
		event.preventDefault();
		setError("");
		setSuccessMessage("");

		if (!canGenerate) {
			setError("Add a product specification and choose between 1 and 100 iterations.");
			return;
		}

		setIsSubmitting(true);

		try {
			const result = await onGenerate({
				product_specification: trimmedProductSpec,
				additional_detail: form.additional_detail.trim() || undefined,
				n_iteration: Number(form.n_iteration) || 10,
			});
			setSuccessMessage(
				`Prompts generated (${result?.prompts_count || 0}). Review and click Start Simulation.`
			);
		} catch (requestError) {
			setError(requestError.message || "Failed to create simulation.");
		} finally {
			setIsSubmitting(false);
		}
	};

	const handleStart = async () => {
		setError("");
		setSuccessMessage("");
		setIsSubmitting(true);
		try {
			const result = await onStartDraft();
			setSuccessMessage(
				`Simulation started (${result?.mode || "processing"}). ID: ${result?.simulation_id || "-"}`
			);
			setTimeout(() => {
				setIsModalOpen(false);
				setSuccessMessage("");
			}, 900);
		} catch (requestError) {
			setError(requestError.message || "Failed to start simulation.");
		} finally {
			setIsSubmitting(false);
		}
	};

	const handleCancelDraft = async () => {
		if (!hasDraft) {
			setIsModalOpen(false);
			return;
		}

		setError("");
		setIsSubmitting(true);
		try {
			await onCancelDraft();
			setIsModalOpen(false);
		} catch (requestError) {
			setError(requestError.message || "Failed to cancel draft.");
		} finally {
			setIsSubmitting(false);
		}
	};

	return (
		<>
			<div className="dashboard-command">
				<div className="dashboard-command-copy">
					<div className="dashboard-eyebrow">Executive command center</div>
					<h1>{companyName}</h1>
					<p>
						Monitor AI visibility, accuracy, competitors, and operational issues from one place.
					</p>
					<div className="dashboard-chip-row">
						<span className="dashboard-chip">Domain · {approvedDomain}</span>
						<span className="dashboard-chip">Role · {userRole}</span>
						<span className="dashboard-chip">Draft prompts · {draftPromptCount}</span>
					</div>
				</div>

				<div className="dashboard-command-panel">
					<div className="dashboard-status-card">
						<div className="dashboard-status-icon">
							<CalendarClock size={18} />
						</div>
						<div>
							<div className="dashboard-status-label">Last simulation</div>
							<div className="dashboard-status-value">{lastSimulationLabel}</div>
								<div className="dashboard-status-meta">
									{lastSimulationStatus ? `Status: ${lastSimulationStatus} · ` : ""}
									{lastSimulationRelative}
								</div>
						</div>
					</div>

					<div className="header-actions header-actions-row">
						<button type="button" className="btn btn-primary btn-pulse" onClick={openModal}>
							<Sparkles size={16} />
							{isReviewMode ? "Review Simulation Draft" : "Create Simulation"}
						</button>
						<p className="last-simulation-text">
							{hasDraft ? "Generated prompts are ready for review." : "Run a new simulation to refresh insights."}
						</p>
					</div>
				</div>
			</div>

			{isModalOpen ? (
				<div className="modal-backdrop" onClick={closeModal}>
					<div
						className="modal simulation-modal simulation-modal-shell"
						onClick={(event) => event.stopPropagation()}
						role="dialog"
						aria-modal="true"
						aria-labelledby="simulation-modal-title"
					>
						<div className="simulation-modal-toolbar">
							<div className="simulation-stepper">
								<span className={`simulation-step ${!isReviewMode ? "active" : "completed"}`}>1. Configure</span>
								<span className={`simulation-step ${isReviewMode ? "active" : ""}`}>2. Review & start</span>
							</div>
							<button type="button" className="modal-icon-button" onClick={closeModal} disabled={isSubmitting} aria-label="Close simulation modal">
								<X size={18} />
							</button>
						</div>

						{isReviewMode ? (
							<>
								<div className="simulation-modal-head">
									<div>
										<h2 id="simulation-modal-title">Review Generated Prompts</h2>
										<p>Validate the prompt set, then launch the simulation to update executive analytics.</p>
									</div>
									<div className="simulation-meta-card">
										<ClipboardList size={18} />
										<div>
											<strong>{formatInteger(draftPromptCount)}</strong>
											<span>prompts generated</span>
										</div>
									</div>
								</div>

								<div className="simulation-highlight-row">
									<div className="simulation-highlight-card">
										<CheckCircle2 size={18} />
										<div>
											<strong>Draft ready</strong>
											<span>Your prompts are already generated and ready to launch.</span>
										</div>
									</div>
									<div className="simulation-highlight-card neutral">
										<WandSparkles size={18} />
										<div>
											<strong>What happens next</strong>
											<span>Starting the simulation refreshes visibility, accuracy, competitor, and action insights.</span>
										</div>
									</div>
								</div>

								<div className="modal-scroll-region">
									<ol className="prompt-review-list">
										{draft.prompts.map((prompt, idx) => (
											<li key={prompt.id || idx} className="prompt-review-item">
												<span className="prompt-review-index">Prompt {idx + 1}</span>
												<span>{prompt.text}</span>
											</li>
										))}
									</ol>
								</div>

								{error ? <div className="alert error">{error}</div> : null}
								{successMessage ? <div className="alert success">{successMessage}</div> : null}

								<div className="modal-actions">
									<button type="button" className="btn btn-secondary" onClick={handleCancelDraft} disabled={isSubmitting}>
										Discard Draft
									</button>
									<button type="button" className="btn btn-primary" onClick={handleStart} disabled={isSubmitting}>
										<PlayCircle size={16} />
										{isSubmitting ? "Starting..." : "Start Simulation"}
									</button>
								</div>
							</>
						) : (
							<form onSubmit={handleGenerate}>
								<div className="simulation-modal-head">
									<div>
										<h2 id="simulation-modal-title">Create Simulation</h2>
										<p>Generate a fresh prompt batch to measure brand visibility, factual quality, and competitor pressure.</p>
									</div>
									<div className="simulation-meta-card">
										<Sparkles size={18} />
										<div>
											<strong>{formatInteger(form.n_iteration)}</strong>
											<span>planned prompts</span>
										</div>
									</div>
								</div>

								<div className="simulation-highlight-row">
									<div className="simulation-highlight-card">
										<Sparkles size={18} />
										<div>
											<strong>Fast setup</strong>
											<span>Choose a product, add optional context, and set how many prompts you want generated.</span>
										</div>
									</div>
									<div className="simulation-highlight-card neutral">
										<WandSparkles size={18} />
										<div>
											<strong>Best results</strong>
											<span>Use a clear product name and include audience, region, or use-case details for more targeted prompts.</span>
										</div>
									</div>
								</div>

								<div className="simulation-checklist">
									{simulationChecklist.map((item) => (
										<div key={item} className="simulation-checklist-item">
											<span className="simulation-checklist-dot" />
											<span>{item}</span>
										</div>
									))}
								</div>

								<label>
									Product specification
									<input
										ref={primaryInputRef}
										name="product_specification"
										value={form.product_specification}
										onChange={updateField}
										placeholder="Laptop, running shoes, CRM platform..."
										required
									/>
									<small className="field-helper">Use the main product or service you want the simulation to evaluate.</small>
								</label>

								<label>
									Additional details (optional)
									<textarea
										name="additional_detail"
										value={form.additional_detail}
										onChange={updateField}
										placeholder="Audience, region, pricing segment, sales problem, or use case"
										rows={3}
									/>
									<div className="field-helper-row">
										<small className="field-helper">Optional context helps generate sharper prompts.</small>
										<small className="field-helper">{detailLength} characters</small>
									</div>
								</label>

								<label>
									Number of iterations
									<input
										name="n_iteration"
										type="number"
										min={1}
										max={100}
										value={form.n_iteration}
										onChange={updateField}
										required
									/>
									<div className="iteration-preset-row" role="group" aria-label="Iteration presets">
										{PRODUCT_PRESETS.map((preset) => (
											<button
												key={preset}
												type="button"
												className={Number(form.n_iteration) === preset ? "iteration-preset active" : "iteration-preset"}
												onClick={() => setForm((prev) => ({ ...prev, n_iteration: preset }))}
											>
												{preset}
											</button>
										))}
									</div>
									<small className="field-helper">Most teams start with 10 to 20 prompts for a balanced first run.</small>
								</label>

								{error ? <div className="alert error">{error}</div> : null}
								{successMessage ? <div className="alert success">{successMessage}</div> : null}

								<div className="modal-actions">
									<button type="button" className="btn btn-secondary" onClick={closeModal} disabled={isSubmitting}>
										Close
									</button>
									<button type="submit" className="btn btn-primary" disabled={isSubmitting || !canGenerate}>
										<Sparkles size={16} />
										{isSubmitting ? "Generating..." : "Generate Prompt Draft"}
									</button>
								</div>
							</form>
						)}
					</div>
				</div>
			) : null}
		</>
	);
}

