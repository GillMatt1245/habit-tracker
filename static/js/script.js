// Auto-save one-liner when typing
document.addEventListener("DOMContentLoaded", function () {
	// Handle memory input (one-liner)
	const memoryInputs = document.querySelectorAll(".memory-input");
	memoryInputs.forEach((input) => {
		let timeout;
		input.addEventListener("input", function () {
			clearTimeout(timeout);
			timeout = setTimeout(() => {
				saveOneLiner(this);
			}, 500); // Save after 500ms of no typing
		});
	});

	// Handle habit checkmarks
	const habitChecks = document.querySelectorAll(".habit-check");
	habitChecks.forEach((check) => {
		check.addEventListener("click", function () {
			toggleHabit(this);
		});
	});

	// Handle habit name editing
	const habitHeaders = document.querySelectorAll(".habit-column-header");
	habitHeaders.forEach((header) => {
		header.addEventListener("blur", function () {
			updateHabitName(this);
		});

		// Save on Enter key
		header.addEventListener("keypress", function (e) {
			if (e.key === "Enter") {
				e.preventDefault();
				this.blur();
			}
		});
	});

	// Handle best day selection
	const bestDaySelect = document.querySelector(".best-day-select");
	if (bestDaySelect) {
		bestDaySelect.addEventListener("change", function () {
			saveBestDay(this);
		});
	}
});

// Save one-liner to database
function saveOneLiner(input) {
	const year = input.dataset.year;
	const month = input.dataset.month;
	const day = input.dataset.day;
	const text = input.value;

	fetch("/api/save-oneliner", {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
		},
		body: JSON.stringify({
			year: parseInt(year),
			month: parseInt(month),
			day: parseInt(day),
			text: text,
		}),
	})
		.then((response) => response.json())
		.then((data) => {
			if (data.status === "success") {
				// Optional: Show save indicator
				showSaveIndicator(input);
			}
		})
		.catch((error) => {
			console.error("Error saving one-liner:", error);
		});
}

// Toggle habit checkmark
function toggleHabit(checkElement) {
	const year = checkElement.dataset.year;
	const month = checkElement.dataset.month;
	const day = checkElement.dataset.day;
	const habitNumber = checkElement.dataset.habit;

	// Toggle visual state
	const isChecked = checkElement.classList.toggle("checked");

	// Save to database
	fetch("/api/save-habit", {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
		},
		body: JSON.stringify({
			year: parseInt(year),
			month: parseInt(month),
			day: parseInt(day),
			habit_number: parseInt(habitNumber),
			checked: isChecked,
		}),
	})
		.then((response) => response.json())
		.then((data) => {
			if (data.status === "success") {
				// Add a little animation
				checkElement.style.transform = "scale(1.1)";
				setTimeout(() => {
					checkElement.style.transform = "";
				}, 200);
			}
		})
		.catch((error) => {
			console.error("Error saving habit:", error);
			// Revert on error
			checkElement.classList.toggle("checked");
		});
}

// Update habit name
function updateHabitName(headerElement) {
	const year = headerElement.dataset.year;
	const month = headerElement.dataset.month;
	const habitNumber = headerElement.dataset.habitNumber;
	const name = headerElement.textContent.trim();

	if (!name) {
		headerElement.textContent = `Habit ${habitNumber}`;
		return;
	}

	fetch("/api/update-habit-name", {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
		},
		body: JSON.stringify({
			year: parseInt(year),
			month: parseInt(month),
			habit_number: parseInt(habitNumber),
			name: name,
		}),
	})
		.then((response) => response.json())
		.then((data) => {
			if (data.status === "success") {
				showSaveIndicator(headerElement);
			}
		})
		.catch((error) => {
			console.error("Error updating habit name:", error);
		});
}

// Save best day selection
function saveBestDay(selectElement) {
	const year = selectElement.dataset.year;
	const month = selectElement.dataset.month;
	const bestDay = selectElement.value;

	if (!bestDay) return;

	fetch("/api/save-best-day", {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
		},
		body: JSON.stringify({
			year: parseInt(year),
			month: parseInt(month),
			best_day: parseInt(bestDay),
		}),
	})
		.then((response) => response.json())
		.then((data) => {
			if (data.status === "success") {
				// Add a subtle highlight
				selectElement.style.background = "#c8e6c9";
				setTimeout(() => {
					selectElement.style.background = "";
				}, 1000);
			}
		})
		.catch((error) => {
			console.error("Error saving best day:", error);
		});
}

// Show save indicator (optional visual feedback)
function showSaveIndicator(element) {
	const originalBackground = element.style.background;
	element.style.background = "#c8e6c9";
	setTimeout(() => {
		element.style.background = originalBackground;
	}, 500);
}

// Keyboard shortcuts
document.addEventListener("keydown", function (e) {
	// Ctrl/Cmd + Left Arrow = Previous month
	if ((e.ctrlKey || e.metaKey) && e.key === "ArrowLeft") {
		e.preventDefault();
		const prevBtn = document.querySelector(".prev-btn");
		if (prevBtn) prevBtn.click();
	}

	// Ctrl/Cmd + Right Arrow = Next month
	if ((e.ctrlKey || e.metaKey) && e.key === "ArrowRight") {
		e.preventDefault();
		const nextBtn = document.querySelector(".next-btn");
		if (nextBtn) nextBtn.click();
	}
});

// Prevent accidental page refresh when editing
let hasUnsavedChanges = false;

document
	.querySelectorAll(".memory-input, .habit-column-header")
	.forEach((element) => {
		element.addEventListener("input", () => {
			hasUnsavedChanges = true;
		});
	});

// Clear flag after saves
document.addEventListener("click", () => {
	setTimeout(() => {
		hasUnsavedChanges = false;
	}, 1000);
});

// Warn before leaving if there are unsaved changes
window.addEventListener("beforeunload", function (e) {
	if (hasUnsavedChanges) {
		e.preventDefault();
		e.returnValue = "";
	}
});
