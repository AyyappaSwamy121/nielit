document.addEventListener('DOMContentLoaded', function() {
    
    // --- PDF Download Logic ---
    const downloadPdfBtn = document.getElementById('downloadPdfBtn');
    if (downloadPdfBtn) {
        downloadPdfBtn.addEventListener('click', function() {
            const element = document.getElementById('dashboardContent');
            const opt = {
                margin:       0.5,
                filename:     'Dashboard_Report.pdf',
                image:        { type: 'jpeg', quality: 0.98 },
                html2canvas:  { scale: 2 },
                jsPDF:        { unit: 'in', format: 'a4', orientation: 'landscape' }
            };
            html2pdf().set(opt).from(element).save();
        });
    }

    // --- Chart Helpers ---
    const getLabels = (data, key) => data.map(item => item[key]);
    const getCounts = (data) => data.map(item => item.count);
    
    // Default Colors
    const bgColors = [
        'rgba(54, 162, 235, 0.6)', 'rgba(255, 99, 132, 0.6)',
        'rgba(255, 206, 86, 0.6)', 'rgba(75, 192, 192, 0.6)',
        'rgba(153, 102, 255, 0.6)', 'rgba(255, 159, 64, 0.6)'
    ];

    // 1. Daily Registrations (Line)
    const ctxDaily = document.getElementById('dailyChart');
    if(ctxDaily && typeof dailyData !== 'undefined') {
        new Chart(ctxDaily, {
            type: 'line',
            data: {
                labels: getLabels(dailyData, 'date'),
                datasets: [{
                    label: 'Registrations',
                    data: getCounts(dailyData),
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1,
                    fill: true,
                    backgroundColor: 'rgba(75, 192, 192, 0.2)'
                }]
            }
        });
    }

    // 2. Monthly Registrations (Bar)
    const ctxMonthly = document.getElementById('monthlyChart');
    if(ctxMonthly && typeof monthlyData !== 'undefined') {
        new Chart(ctxMonthly, {
            type: 'bar',
            data: {
                labels: getLabels(monthlyData, 'month'),
                datasets: [{
                    label: 'Registrations',
                    data: getCounts(monthlyData),
                    backgroundColor: 'rgba(54, 162, 235, 0.6)'
                }]
            }
        });
    }

    // 3. Gender Breakdown (Pie)
    const ctxGender = document.getElementById('genderChart');
    if(ctxGender && typeof genderData !== 'undefined') {
        new Chart(ctxGender, {
            type: 'pie',
            data: {
                labels: getLabels(genderData, 'gender'),
                datasets: [{ data: getCounts(genderData), backgroundColor: bgColors }]
            }
        });
    }

    // 4. Community Stats (Doughnut)
    const ctxCommunity = document.getElementById('communityChart');
    if(ctxCommunity && typeof communityData !== 'undefined') {
        new Chart(ctxCommunity, {
            type: 'doughnut',
            data: {
                labels: getLabels(communityData, 'community__name'),
                datasets: [{ data: getCounts(communityData), backgroundColor: bgColors }]
            }
        });
    }

    // 5. Program Distribution (Bar)
    const ctxProgram = document.getElementById('programChart');
    if(ctxProgram && typeof programData !== 'undefined') {
        new Chart(ctxProgram, {
            type: 'bar',
            data: {
                labels: getLabels(programData, 'program_opting__name'),
                datasets: [{
                    label: 'Students',
                    data: getCounts(programData),
                    backgroundColor: 'rgba(153, 102, 255, 0.6)'
                }]
            }
        });
    }

    // 6. State-wise Analytics (Bar)
    const ctxState = document.getElementById('stateChart');
    if(ctxState && typeof stateData !== 'undefined') {
        new Chart(ctxState, {
            type: 'bar',
            data: {
                labels: getLabels(stateData, 'state__name'),
                datasets: [{
                    label: 'Applications',
                    data: getCounts(stateData),
                    backgroundColor: 'rgba(255, 159, 64, 0.6)'
                }]
            }
        });
    }

    // 7. District-wise Analytics (Line/Bar)
    const ctxDistrict = document.getElementById('districtChart');
    if(ctxDistrict && typeof districtData !== 'undefined') {
        new Chart(ctxDistrict, {
            type: 'bar',
            data: {
                labels: getLabels(districtData, 'district__name'),
                datasets: [{
                    label: 'Applications',
                    data: getCounts(districtData),
                    backgroundColor: 'rgba(255, 99, 132, 0.6)'
                }]
            }
        });
    }
});
