let currentDate = new Date();

function renderMonthView(date) {
    const calendarBody = document.getElementById("monthCalendarBody");
    const monthYearHeading = document.getElementById("monthYearHeading");

    const year = date.getFullYear();
    const month = date.getMonth();
    const monthNames = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ];
    monthYearHeading.textContent = `${monthNames[month]} ${year}`;

    const firstDay = new Date(year, month, 1);
    const startDay = firstDay.getDay();
    const lastDate = new Date(year, month + 1, 0).getDate();

    calendarBody.innerHTML = "";
    let dateCounter = 1;

    for (let i = 0; i < 6; i++) {
        const row = document.createElement("tr");
        for (let j = 0; j < 7; j++) {
            const cell = document.createElement("td");
            cell.classList.add("month-day-cell");

            if ((i === 0 && j < startDay) || dateCounter > lastDate) {
                cell.innerHTML = "";
            } else {
                const dayDate = new Date(year, month, dateCounter);
                const formattedDate = `${year}-${String(month + 1).padStart(2, '0')}-${String(dateCounter).padStart(2, '0')}`;

                const dayAppointments = appointments.filter(appt =>
                    appt.start.startsWith(formattedDate)
                );

                const normalAppointments = dayAppointments.filter(appt =>
                    !appt.type.startsWith("Test")
                );

                const testAppointments = dayAppointments.filter(appt =>
                    appt.type.startsWith("Test")
                );

                const dayDocuments = documents.filter(doc =>
                    doc.start.startsWith(formattedDate)
                );

                const expiringDocs = documents.filter(doc =>
                    doc.expiration_date === formattedDate
                );

                cell.innerHTML = `<strong>${dateCounter}</strong>`;

                normalAppointments.forEach(appt => {
                    const apptDiv = document.createElement("div");
                    apptDiv.classList.add("badge", "btn-Appointment", "text-dark", "mt-1", "text-truncate");
                    apptDiv.style.maxWidth = "100%";
                    apptDiv.textContent = `${appt.type} @ ${appt.start.slice(11, 16)}`;
                    cell.appendChild(apptDiv);
                });

                testAppointments.forEach(appt => {
                    const testDiv = document.createElement("div");
                    testDiv.classList.add("badge", "btn-Missed", "text-dark", "mt-1", "d-block", "text-truncate");
                    testDiv.style.maxWidth = "100%";
                    testDiv.textContent = ` ${appt.type} @ ${appt.start.slice(11, 16)}`;
                    cell.appendChild(testDiv);
                });

                dayDocuments.forEach(doc => {
                    const docDiv = document.createElement("div");
                    docDiv.classList.add("badge", "btn-Tests", "text-dark", "mt-1", "d-block", "text-truncate");
                    docDiv.style.maxWidth = "100%";
                    docDiv.textContent = ` @ ${doc.type}`;
                    cell.appendChild(docDiv);
                });

                expiringDocs.forEach(doc => {
                    const expDiv = document.createElement("div");
                    expDiv.classList.add("card", "btn-Expirations", "text-dark", "mt-2", "d-block");
                    expDiv.style.maxWidth = "100%";
                    expDiv.textContent = ` ${doc.type} expires today!`;
                    cell.appendChild(expDiv);
                });

                // Click handler for tooltip
                cell.addEventListener("click", (e) => {
                    const tooltip = document.getElementById("cellTooltip");
                    let html = `<strong>${formattedDate}</strong><br><hr>`;

                    if (dayAppointments.length > 0) {
                        html += "<h5>Appointments</h5>";
                        dayAppointments.forEach(appt => {
                            html += `<div><strong>${appt.title}</strong><br>${appt.description || "No notes"}<br>${appt.start.slice(11, 16)} to ${appt.end.slice(11, 16)}<br>Location: ${appt.location}</div><hr>`;
                        });
                    }

                    if (dayDocuments.length > 0) {
                        html += "<h5>Uploaded Documents</h5>";
                        dayDocuments.forEach(doc => {
                            html += `<div><strong>${doc.title}</strong><br>${doc.description}<br>Expires: ${doc.expiration_date}</div><hr>`;
                        });
                    }

                    if (expiringDocs.length > 0) {
                        html += "<h5>Expiring Documents</h5>";
                        expiringDocs.forEach(doc => {
                            html += `<div><strong>${doc.title}</strong><br>Expires Today!</div><hr>`;
                        });
                    }

                    if (dayAppointments.length === 0 && dayDocuments.length === 0 && expiringDocs.length === 0) {
                        html += "<p>No events on this day.</p>";
                    }

                    document.getElementById("tooltipContent").innerHTML = html;

                    // Position tooltip
                    const rect = cell.getBoundingClientRect();
                    tooltip.style.top = `${window.scrollY + rect.bottom + 5}px`;
                    tooltip.style.left = `${window.scrollX + rect.left}px`;
                    tooltip.style.display = "block";
                });

                dateCounter++;
            }

            row.appendChild(cell);
        }
        calendarBody.appendChild(row);
        if (dateCounter > lastDate) break;
    }
}

document.addEventListener('DOMContentLoaded', function () {
    renderMonthView(currentDate);

    document.getElementById("prevMonth").addEventListener("click", function () {
        currentDate.setMonth(currentDate.getMonth() - 1);
        renderMonthView(currentDate);
    });

    document.getElementById("nextMonth").addEventListener("click", function () {
        currentDate.setMonth(currentDate.getMonth() + 1);
        renderMonthView(currentDate);
    });
});
