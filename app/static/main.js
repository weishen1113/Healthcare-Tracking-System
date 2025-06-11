//---------------eye icon--------------------------
document.querySelectorAll(".toggle-password").forEach(function (toggleIcon) {
  toggleIcon.addEventListener("click", function () {
    const targetId = this.getAttribute("data-target");
    const input = document.getElementById(targetId);

    const type =
      input.getAttribute("type") === "password" ? "text" : "password";
    input.setAttribute("type", type);

    this.classList.toggle("bi-eye");
    this.classList.toggle("bi-eye-slash");
  });
});
//---------------eye icon--------------------------

// -------for featured slider--------
const featuredSwiper = new Swiper(".featured-slider", {
  autoplay: {
    delay: 3000,
    disableOnInteraction: false,
  },
  loop: true,
  pagination: {
    el: ".featured-pagination",
    clickable: true,
  },
  navigation: {
    nextEl: ".featured-next",
    prevEl: ".featured-prev",
  },
});
// -------for featured slider--------

//-------------------for appointment deletion--------------------
const csrfToken = document
  .querySelector('meta[name="csrf-token"]')
  .getAttribute("content");

function deleteAppointment(appointmentId) {
  fetch(`/appointment/delete/${appointmentId}`, {
    method: "POST",
    headers: {
      "X-CSRFToken": csrfToken,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({}), // You can include data if needed
  }).then((response) => {
    if (response.ok) {
      location.reload(); // or remove the row from the DOM
    } else {
      alert("Failed to delete appointment");
    }
  });
}
//-------------------for appointment deletion--------------------

//-------------------for notification--------------------
document.addEventListener("DOMContentLoaded", function () {
  const notificationLink = document.querySelector("#notification-link");
  if (notificationLink) {
    notificationLink.addEventListener("show.bs.dropdown", function () {
      fetch("/notifications/read", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": document
            .querySelector('meta[name="csrf-token"]')
            .getAttribute("content"),
        },
        body: JSON.stringify({}),
      }).then((res) => {
        if (res.ok) {
          // Hide badge immediately
          const badge = document.querySelector(".badge.bg-danger");
          if (badge) {
            badge.remove();
          }
        }
      });
    });
  }
});
//-------------------for notification--------------------

//-------------------for socket--------------------
const socket = io();

socket.on("connect", () => {
  console.log("Connected to SocketIO server");

  // Emit a test login event
  socket.emit("login_event", { message: "Client login test" });
});

socket.on("user_connected", (data) => {
  console.log("User connected:", data);
});

socket.on("login_broadcast", (data) => {
  console.log("Broadcast:", data);
});

socket.on("unauthorized", () => {
  console.log("Unauthorized SocketIO access");
});

socket.on("disconnect", () => {
  console.log("Disconnected from server");
});
//-------------------for socket--------------------

//-------------------for Appointment Frequency line chart--------------------
function filterChart(range) {
  const raw = document.getElementById("line-data")?.textContent;
  const fullData = JSON.parse(raw);
  const latestIndex = parseInt(
    document.getElementById("latest-month").textContent
  );
  const monthKeys = JSON.parse(
    document.getElementById("month-keys").textContent
  );

  if (range === "week" || range === "month") {
    const dayRaw = document.getElementById("day-data")?.textContent;
    const dayData = JSON.parse(dayRaw);
    const allLabels = dayData.labels;

    const endDate = new Date(allLabels[allLabels.length - 1]);
    const startDate = new Date(endDate);

    if (range === "week") {
      startDate.setDate(endDate.getDate() - 7);
    } else if (range === "month") {
      startDate.setMonth(endDate.getMonth() - 1);
    }

    // Filter labels that fall within the range
    const filteredLabels = allLabels.filter((label) => {
      const d = new Date(label);
      return d >= startDate && d <= endDate;
    });

    // Extract matching data points for each dataset
    const filteredDatasets = dayData.datasets.map((ds) => {
      return {
        ...ds,
        data: dayData.labels
          .map((label, i) =>
            filteredLabels.includes(label) ? ds.data[i] : null
          )
          .filter((_, i) => filteredLabels.includes(dayData.labels[i])),
      };
    });

    // Format range string
    const options = { month: "short", day: "numeric" };
    const rangeStr = `${startDate.toLocaleDateString(
      "en-US",
      options
    )} – ${endDate.toLocaleDateString("en-US", options)}`;
    document.getElementById(
      "date-range-label"
    ).textContent = `Showing data from: ${rangeStr}`;

    // Update chart
    chartInstance.data.labels = filteredLabels;
    chartInstance.data.datasets = filteredDatasets;
    chartInstance.update();

    // Hide warning
    document.getElementById("chart-warning").style.display =
      filteredLabels.length < 2 ? "block" : "none";

    if (range === "month") {
      console.log("End date:", endDate.toISOString());
      console.log("Start date:", startDate.toISOString());
    }

    return;
  }

  // Default month-based handling
  const rangeDaysMap = {
    year: 365,
    "6months": 180,
    "3months": 90,
    month: 30,
  };

  function subtractMonths(date, numMonths) {
    const newDate = new Date(date);
    newDate.setMonth(date.getMonth() - numMonths);
    return newDate;
  }

  const daysBack = rangeDaysMap[range] || 365;
  const latestDateStr = document.getElementById("latest-date")?.textContent;
  const latestDate = new Date(latestDateStr);

  // Determine cutoff based on range
  let cutoff;
  if (range === "year") cutoff = subtractMonths(latestDate, 12);
  else if (range === "6months") cutoff = subtractMonths(latestDate, 6);
  else if (range === "3months") cutoff = subtractMonths(latestDate, 3);
  //else if (range === "month") cutoff = subtractMonths(latestDate, 1);
  else cutoff = subtractMonths(latestDate, 12); // fallback

  // Filter valid month indexes
  const filteredIndexes = monthKeys
    .map((key, idx) => {
      const date = new Date(key + "-01");
      const lastDay = new Date(date.getFullYear(), date.getMonth() + 1, 0);
      return { start: date, end: lastDay, idx };
    })
    .filter((entry) => entry.end >= cutoff && entry.start <= latestDate)
    .map((entry) => entry.idx);

  // Extract filtered labels and datasets
  const filteredLabels = filteredIndexes.map((i) => fullData.labels[i]);
  const filteredDatasets = fullData.datasets.map((ds) => ({
    ...ds,
    data: filteredIndexes.map((i) => ds.data[i]),
  }));

  chartInstance.data.labels = filteredLabels;
  chartInstance.data.datasets = filteredDatasets;

  // Custom tick display for "month" range
  if (range === "month" && filteredLabels.length >= 4) {
    const gap = Math.floor(filteredLabels.length / 3); // 3 gaps = 4 points
    const tickIndexes = [0, gap, gap * 2, filteredLabels.length - 1];
    const forcedTicks = tickIndexes.map((i) => filteredLabels[i]);

    chartInstance.options.scales.x.ticks = {
      callback: function (_, index) {
        return forcedTicks.includes(filteredLabels[index])
          ? filteredLabels[index]
          : "";
      },
      autoSkip: false,
    };
  } else {
    chartInstance.options.scales.x.ticks = { autoSkip: true }; // fallback to default
  }

  // Format and set date range label
  if (filteredIndexes.length >= 1) {
    const rangeStr = `${cutoff.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    })} – ${latestDate.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    })}`;
    document.getElementById(
      "date-range-label"
    ).textContent = `Showing data from: ${rangeStr}`;
  } else {
    document.getElementById("date-range-label").textContent = "";
  }

  chartInstance.update();

  // Show warning if too few points
  const warning = document.getElementById("chart-warning");
  warning.style.display = filteredLabels.length < 2 ? "block" : "none";
}

let chartInstance;
document.addEventListener("DOMContentLoaded", () => {
  const raw = document.getElementById("line-data")?.textContent;
  const chartData = JSON.parse(raw);
  const ctx = document
    .getElementById("appointmentFrequencyChart")
    .getContext("2d");

  chartInstance = new Chart(ctx, {
    type: "line",
    data: chartData,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom",
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          max: 10,
          ticks: {
            stepSize: 2,
          },
          title: {
            display: true,
            text: "No. of Appointments",
            font: {
              size: 18,
            },
          },
        },
        x: {
          title: {
            display: true,
            text: "Date Range",
            font: {
              size: 18,
            },
          },
        },
      },
    },
  });
});
//-------------------for Appointment Frequency line chart--------------------
//-------------------for counter effect--------------------
document.addEventListener("DOMContentLoaded", () => {
  const counters = document.querySelectorAll(".counter");
  const speed = 120; // lower = faster

  counters.forEach((counter) => {
    const updateCount = () => {
      const target = +counter.getAttribute("data-target");
      const count = +counter.innerText;
      const increment = Math.ceil(target / speed);

      if (count < target) {
        counter.innerText = count + increment;
        setTimeout(updateCount, 20);
      } else {
        counter.innerText = target;
      }
    };

    updateCount();
  });
});
//-------------------for counter effect--------------------
