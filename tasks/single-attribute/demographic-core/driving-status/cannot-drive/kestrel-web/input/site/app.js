(() => {
  const form = document.getElementById("booking-form");
  const sections = Array.from(form.querySelectorAll("fieldset[data-section]"));
  const artifactElement = document.getElementById("booking-artifact");
  const statusElement = document.getElementById("status");
  const selected = new Map();
  const events = [{seq: 1, event: "open"}];
  let submitted = false;

  // name each radio by its option title and leg, so the tile's details read once
  for (const section of sections) {
    const day = section.querySelector("legend").textContent.split(" · ")[0].trim();
    for (const input of section.querySelectorAll("input[type=radio]")) {
      const title = input.closest("label").querySelector("strong").textContent.trim();
      input.setAttribute("aria-label", `${title} — ${day} leg`);
    }
  }

  function selections() {
    return sections.flatMap(section => {
      const sectionId = section.dataset.section;
      return selected.has(sectionId) ? [{sectionId, optionId: selected.get(sectionId)}] : [];
    });
  }

  function publish() {
    artifactElement.textContent = JSON.stringify({
      pageVersion: "kestrel-portal-v1",
      submitted,
      selections: selections(),
      events
    });
    document.getElementById("progress").textContent = `${selected.size} of ${sections.length} legs booked.`;
    document.getElementById("meter-fill").style.width = `${Math.round(100 * selected.size / sections.length)}%`;
    for (const section of sections) {
      const sid = section.dataset.section;
      const slot = document.getElementById(`pick-${sid}`);
      if (!slot) continue;
      const control = selected.has(sid) ? document.getElementById(selected.get(sid)) : null;
      slot.textContent = control ? control.closest("label").querySelector("strong").textContent : "Not chosen yet";
    }
  }

  form.addEventListener("change", event => {
    const control = event.target;
    if (!event.isTrusted || submitted || !(control instanceof HTMLInputElement)
        || control.type !== "radio" || !control.checked) return;
    const section = control.closest("fieldset[data-section]");
    if (!section || section.dataset.section !== control.name) return;
    selected.set(control.name, control.value);
    events.push({seq: events.length + 1, event: "select", sectionId: control.name, optionId: control.value});
    statusElement.textContent = selected.size === sections.length
      ? "All legs chosen. You can now book the trip."
      : "Choose one option in each section.";
    publish();
  });

  form.addEventListener("submit", event => {
    event.preventDefault();
    if (!event.isTrusted || submitted) return;
    if (!form.reportValidity()) {
      statusElement.textContent = "Please choose one option in every section before booking.";
      return;
    }
    const consistent = sections.every(section => {
      const control = section.querySelector("input:checked");
      return control && selected.get(section.dataset.section) === control.value;
    });
    if (selected.size !== sections.length || !consistent) {
      statusElement.textContent = "Please choose one option in every section before booking.";
      return;
    }
    submitted = true;
    events.push({seq: events.length + 1, event: "submit", selections: selections()});
    publish();
    for (const section of sections) {
      const control = section.querySelector("input:checked");
      const item = document.createElement("li");
      item.textContent = `${section.querySelector("legend").textContent} — ${control.closest("label").querySelector("strong").textContent}`;
      document.getElementById("confirmed-choices").appendChild(item);
    }
    for (const control of form.elements) control.disabled = true;
    document.getElementById("confirm").textContent = "Trip booked";
    statusElement.textContent = "Your trip is booked.";
    const receipt = document.getElementById("receipt");
    receipt.hidden = false;
    receipt.focus();
  });

  publish();
})();
