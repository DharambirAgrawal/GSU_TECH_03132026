import { useState } from "react";

export default function DashboardHeader({ profile, onGenerate, onCancelDraft, hasDraft }) {
	const [isModalOpen, setIsModalOpen] = useState(false);
	const [isSubmitting, setIsSubmitting] = useState(false);
	const [error, setError] = useState("");
	const [form, setForm] = useState({
		product_specification: "",
		additional_detail: "",
		n_iteration: 10,
	});

	const openModal = () => {
		setError("");
		setIsModalOpen(true);
	};

	const closeModal = () => {
		if (isSubmitting) return;
		setIsModalOpen(false);
	};

	const updateField = (event) => {
		const { name, value } = event.target;
		setForm((prev) => ({ ...prev, [name]: name === "n_iteration" ? Number(value) : value }));
	};

	const handleGenerate = async (event) => {
		event.preventDefault();
		setError("");
		setIsSubmitting(true);

		try {
			await onGenerate({
				product_specification: form.product_specification.trim(),
				additional_detail: form.additional_detail.trim() || undefined,
				n_iteration: Number(form.n_iteration),
			});
			setIsModalOpen(false);
		} catch (requestError) {
			setError(requestError.message || "Failed to create simulation.");
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
			<div className="workspace-header-row">
				<div>
					<h1>{profile?.company?.name || "Dashboard"}</h1>
					<p>
						Domain: {profile?.company?.approved_email_domain || "-"} · Role: {profile?.user?.role || "member"}
					</p>
				</div>
				<button type="button" className="btn btn-primary" onClick={openModal}>
					Create Simulation
				</button>
			</div>

			{isModalOpen ? (
				<div className="modal-backdrop" onClick={closeModal}>
					<form className="modal simulation-modal" onSubmit={handleGenerate} onClick={(event) => event.stopPropagation()}>
						<h2>Create Simulation</h2>
						<p>Enter required fields and generate prompts for a simulation draft.</p>

						<label>
							Product specification
							<input
								name="product_specification"
								value={form.product_specification}
								onChange={updateField}
								placeholder="Laptop"
								required
							/>
						</label>

						<label>
							Additional detail (optional)
							<textarea
								name="additional_detail"
								value={form.additional_detail}
								onChange={updateField}
								placeholder="Target budget, audience, and use case"
								rows={3}
							/>
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
						</label>

						{error ? <div className="alert error">{error}</div> : null}

						<div className="modal-actions">
							<button type="button" className="btn btn-secondary" onClick={handleCancelDraft} disabled={isSubmitting}>
								Cancel
							</button>
							<button type="submit" className="btn btn-primary" disabled={isSubmitting}>
								{isSubmitting ? "Generating..." : "Generate"}
							</button>
						</div>
					</form>
				</div>
			) : null}
		</>
	);
}

