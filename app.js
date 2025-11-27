// Constants
const PASSWORD = "88888"; // System password
const PLAYERS_CSV = "player_statistics.csv";
const RECORDS_CSV = "team_building_record.csv";

// DOM Elements
const loginContainer = document.getElementById("login-container");
const mainContainer = document.getElementById("main-container");
const passwordInput = document.getElementById("password-input");
const loginButton = document.getElementById("login-button");
const loginError = document.getElementById("login-error");
const navItems = document.querySelectorAll(".nav-item");
const sections = document.querySelectorAll(".section");
const playerList = document.getElementById("player-list");
const validateButton = document.getElementById("validate-button");
const updateLeaderboardButton = document.getElementById("update-leaderboard-button");
const validationResult = document.getElementById("validation-result");
const validationMessage = document.getElementById("validation-message");
const gameSummary = document.getElementById("game-summary");
const summaryTableBody = document.getElementById("summary-table-body");
const leaderboardTableBody = document.getElementById("leaderboard-table-body");
// Add Player elements
const newPlayerNameInput = document.getElementById("new-player-name");
const addPlayerBtn = document.getElementById("add-player-btn");
// New DOM elements for history feature
const historyDateInput = document.getElementById("history-date");
const searchHistoryBtn = document.getElementById("search-history-btn");
const historyResult = document.getElementById("history-result");
const historyTableBody = document.getElementById("history-table-body");
const selectedDateSpan = document.getElementById("selected-date");
const noRecordsMessage = document.getElementById("no-records-message");
const saveHistoryBtnContainer = document.getElementById("save-history-btn-container");

// Global Variables
let playerStats = [];
let gameRecords = [];
let currentGameData = {
    date: "",
    serviceFee: 0,
    players: []
};

// Event Listeners
document.addEventListener("DOMContentLoaded", init);
loginButton.addEventListener("click", handleLogin);
passwordInput.addEventListener("keyup", (e) => {
    if (e.key === "Enter") handleLogin();
});

navItems.forEach(item => {
    item.addEventListener("click", () => {
        const targetSection = item.getAttribute("data-section");
        switchSection(targetSection);
    });
});

validateButton.addEventListener("click", validateGameData);

// Add Player button event listener
addPlayerBtn.addEventListener("click", addNewPlayer);
// Allow Enter key to add player
newPlayerNameInput.addEventListener("keyup", (e) => {
    if (e.key === "Enter") addNewPlayer();
});

// Add Update LeaderBoard button event listener
updateLeaderboardButton.addEventListener("click", updateLeaderboardWithNewData);

// Add history search button event listener
searchHistoryBtn && searchHistoryBtn.addEventListener("click", searchHistoryRecords);

// Add event listener for save leaderboard button
document.addEventListener("DOMContentLoaded", function() {
    document.getElementById('saveLeaderboardBtn').addEventListener('click', saveLeaderboardAsImage);
    document.getElementById('saveHistoryBtn').addEventListener('click', saveHistoryAsImage);
});

// Initialize the application
async function init() {
    try {
        // Load player statistics
        await loadPlayerStatistics();
        
        // Load game records (移到更新排行榜之前)
        await loadGameRecords();
        
        // Generate player list
        generatePlayerList();
        
        // Update leaderboard
        updateLeaderboard();
        
    } catch (error) {
        console.error("Failed to initialize application:", error);
    }
}

// Load player statistics from CSV
async function loadPlayerStatistics() {
    try {
        const response = await fetch(PLAYERS_CSV);
        const csvData = await response.text();
        
        // Parse CSV data
        Papa.parse(csvData, {
            header: true,
            complete: (results) => {
                playerStats = results.data.filter(player => player.Player); // Filter out empty rows
                
                // Sort by ranking
                playerStats.sort((a, b) => parseInt(a.Ranking) - parseInt(b.Ranking));
                
                // Generate player list in the UI
                generatePlayerList();
                
                // Update leaderboard
                updateLeaderboard();
            }
        });
    } catch (error) {
        console.error("Failed to load player statistics:", error);
    }
}

// Load game records from CSV
async function loadGameRecords() {
    try {
        const response = await fetch(RECORDS_CSV);
        const csvData = await response.text();
        
        console.log("Loaded CSV data, first 100 chars:", csvData.substring(0, 100));
        
        // Parse CSV data
        Papa.parse(csvData, {
            header: true,
            complete: (results) => {
                console.log("Parsed CSV data, row count:", results.data.length);
                console.log("Sample CSV headers:", results.meta.fields);
                
                // 过滤掉没有Time或Player的记录
                gameRecords = results.data.filter(record => record.Time && record.Player);
                console.log("Filtered records count:", gameRecords.length);
                
                // 保留原始格式，不进行格式转换
                // 如果后续需要日期比较，再根据需要转换
                
                // 加载完游戏记录后立即更新最新记录时间
                updateLatestRecordTime();
            }
        });
    } catch (error) {
        console.error("Failed to load game records:", error);
    }
}

// Generate player list
function generatePlayerList() {
    // Clear player list
    playerList.innerHTML = "";
    
    // Generate player cards
    playerStats.forEach(player => {
        createPlayerCard(player);
    });
}

// Create player card
function createPlayerCard(player) {
    const card = document.createElement("div");
    card.className = "player-card";
    card.innerHTML = `
        <div class="player-header">
            <span class="player-name">${player.Player}</span>
            <span class="player-ranking">Ranking: #${player.Ranking}</span>
        </div>
        <div class="player-options">
            <div class="option-row">
                <label>Participate:</label>
                <button class="toggle-button attend-toggle" data-player="${player.Player}">False</button>
            </div>
            <div class="option-row">
                <label>Win/Lose:</label>
                <button class="toggle-button win-lose-toggle win" data-player="${player.Player}">Win</button>
            </div>
            <div class="option-row">
                <label>Chips:</label>
                <input type="number" class="chip-input" data-player="${player.Player}" value="0" disabled>
            </div>
        </div>
    `;
    
    playerList.appendChild(card);
    
    // Add event listeners for toggle buttons and chip input
    setupPlayerCardEventListeners(card);
}

// Setup event listeners for player card
function setupPlayerCardEventListeners(card) {
    // Add event listener for attend toggle
    const attendToggle = card.querySelector(".attend-toggle");
    attendToggle.addEventListener("click", function() {
        const isAttending = this.textContent === "True";
        this.textContent = isAttending ? "False" : "True";
        this.classList.toggle("active", !isAttending);
        
        const playerName = this.getAttribute("data-player");
        const winLoseToggle = card.querySelector(".win-lose-toggle");
        const chipInput = card.querySelector(".chip-input");
        
        // Enable/disable win-lose toggle and chip input based on attendance
        winLoseToggle.disabled = isAttending;
        chipInput.disabled = isAttending;
        
        if (isAttending) {
            // Reset values when attendance is set to false
            winLoseToggle.textContent = "Win";
            winLoseToggle.className = "toggle-button win-lose-toggle win";
            chipInput.value = "0";
        }
        
        // Enable validate button
        validateButton.disabled = false;
        validationResult.classList.add("hidden");
    });
    
    // Add event listener for win-lose toggle
    const winLoseToggle = card.querySelector(".win-lose-toggle");
    winLoseToggle.addEventListener("click", function() {
        const isWin = this.textContent === "Win";
        this.textContent = isWin ? "Lose" : "Win";
        
        if (isWin) {
            this.classList.remove("win");
            this.classList.add("lose");
        } else {
            this.classList.remove("lose");
            this.classList.add("win");
        }
        
        const playerName = this.getAttribute("data-player");
        const chipInput = card.querySelector(".chip-input");
        
        // Set chips to negative if lose, positive if win
        if (this.textContent === "Lose" && parseInt(chipInput.value) > 0) {
            chipInput.value = -parseInt(chipInput.value);
        } else if (this.textContent === "Win" && parseInt(chipInput.value) < 0) {
            chipInput.value = Math.abs(parseInt(chipInput.value));
        }
        
        // Enable validate button
        validateButton.disabled = false;
        validationResult.classList.add("hidden");
    });
    
    // Add event listener for chip input
    const chipInput = card.querySelector(".chip-input");
    chipInput.addEventListener("input", function() {
        const winLoseToggle = card.querySelector(".win-lose-toggle");
        const chipsValue = parseInt(this.value) || 0;
        
        // Update win/lose toggle based on chips value
        if (chipsValue > 0 && winLoseToggle.textContent === "Lose") {
            winLoseToggle.textContent = "Win";
            winLoseToggle.classList.remove("lose");
            winLoseToggle.classList.add("win");
        } else if (chipsValue < 0 && winLoseToggle.textContent === "Win") {
            winLoseToggle.textContent = "Lose";
            winLoseToggle.classList.remove("win");
            winLoseToggle.classList.add("lose");
        }
        
        // Enable validate button
        validateButton.disabled = false;
        validationResult.classList.add("hidden");
    });
}

// Handle login attempt
function handleLogin() {
    const password = passwordInput.value.trim();
    
    if (password === PASSWORD) {
        loginContainer.classList.add("hidden");
        mainContainer.classList.remove("hidden");
    } else {
        loginError.textContent = "Incorrect password, please try again.";
        passwordInput.value = "";
    }
}

// Switch between sections
function switchSection(sectionId) {
    navItems.forEach(item => {
        item.classList.toggle("active", item.getAttribute("data-section") === sectionId);
    });
    
    sections.forEach(section => {
        section.classList.toggle("active", section.id === sectionId);
    });
}

// Validate game data
function validateGameData() {
    const date = document.getElementById("game-date").value;
    const serviceFee = parseFloat(document.getElementById("service-fee").value);
    
    if (!date) {
        showValidationError("Please enter the game date.");
        return;
    }
    
    if (isNaN(serviceFee) || serviceFee < 0) {
        showValidationError("Please enter a valid service fee.");
        return;
    }
    
    const attendingPlayers = [];
    
    document.querySelectorAll(".player-card").forEach(card => {
        const playerName = card.querySelector(".player-name").textContent;
        const isAttending = card.querySelector(".attend-toggle").textContent === "True";
        
        if (isAttending) {
            const winLoseToggle = card.querySelector(".win-lose-toggle");
            const winOrLose = winLoseToggle.textContent; // "Win" or "Lose"  or "Peace"
            const chipsValue = parseInt(card.querySelector(".chip-input").value) || 0;
            
            // Ensure win/lose matches chips value (allow 0 for Peace)
            if (chipsValue > 0 && winOrLose !== "Win") {
                showValidationError(`${playerName}'s chips value does not match win/lose status.`);
                return;
            }
            if (chipsValue < 0 && winOrLose !== "Lose") {
                showValidationError(`${playerName}'s chips value does not match win/lose status.`);
                return;
            }
            
            // For chips = 0, set status to Peace
            let finalWinOrLose = winOrLose;
            if (chipsValue === 0) {
                finalWinOrLose = "Peace";
            }
            
            attendingPlayers.push({
                playerName,
                winOrLose: finalWinOrLose,
                chips: chipsValue,
                finalChips: 0 // Will be calculated later
            });
        }
    });
    
    if (attendingPlayers.length === 0) {
        showValidationError("At least one player must participate in the game.");
        return;
    }
    
    // Calculate the sum of chips
    const chipsSum = attendingPlayers.reduce((sum, player) => sum + player.chips, 0);
    
    // Sum of chips should be zero (winners win what losers lose)
    if (chipsSum !== 0) {
        showValidationError(`chips 总和需为0. 当前总和: ${chipsSum}`);
        return;
    }
    
    // Calculate total win chips (sum of all positive chips)
    const totalWinChips = attendingPlayers
        .filter(player => player.chips > 0)
        .reduce((sum, player) => sum + player.chips, 0);
    
    // Calculate service fee for each player
    attendingPlayers.forEach(player => {
        let playerServiceFee = 0;
        
        // Only winners (chips > 0) pay service fee, proportional to their winnings
        if (player.chips > 0) {
            playerServiceFee = (player.chips / totalWinChips) * serviceFee;
        }
        
        // Final chips is original chips minus service fee
        player.finalChips = player.chips - playerServiceFee;
        player.serviceFee = playerServiceFee;
    });
    
    // Store current game data
    currentGameData = {
        date: formatDate(date),
        serviceFee,
        players: attendingPlayers
    };
    
    // Show validation success and game summary
    showValidationSuccess(attendingPlayers);
}

// Show validation error
function showValidationError(message) {
    validationResult.classList.remove("hidden", "validation-success");
    validationResult.classList.add("validation-error");
    validationMessage.textContent = message;
    gameSummary.classList.add("hidden");
}

// Show validation success
function showValidationSuccess(players) {
    validationResult.classList.remove("hidden", "validation-error");
    validationResult.classList.add("validation-success");
    validationMessage.textContent = "Validation passed! The sum of all players' chips is 0.";
    
    // Display game summary
    showGameSummary(players);
    
    // Hide standard save button and show update leaderboard button
    updateLeaderboardButton.disabled = false;
}

// Show game summary
function showGameSummary(players) {
    gameSummary.classList.remove("hidden");
    summaryTableBody.innerHTML = "";
    
    players.forEach(player => {
        const row = document.createElement("tr");
        
        row.innerHTML = `
            <td>${player.playerName}</td>
            <td>Yes</td>
            <td>${player.winOrLose}</td>
            <td>${player.chips}</td>
            <td>${player.serviceFee.toFixed(2)}</td>
            <td>${player.finalChips.toFixed(2)}</td>
        `;
        
        summaryTableBody.appendChild(row);
    });
}

// Update player statistics
function updatePlayerStatistics() {
    // Create a map to hold player stats
    const statsMap = new Map();
    
    // Initialize with existing player stats
    playerStats.forEach(player => {
        statsMap.set(player.Player, {
            Player: player.Player,
            WinChips: parseInt(player.WinChips) || 0,
            AttendCount: parseInt(player.AttendCount) || 0,
            WinCount: parseInt(player.WinCount) || 0,
            LoseCount: parseInt(player.LoseCount) || 0,
            PeaceCount: parseInt(player.PeaceCount) || 0
        });
    });
    
    // Process all game records
    gameRecords.forEach(record => {
        const playerName = record.Player;
        const finalChips = parseFloat(record.FinalChips);
        
        if (!statsMap.has(playerName)) {
            statsMap.set(playerName, {
                Player: playerName,
                WinChips: 0,
                AttendCount: 0,
                WinCount: 0,
                LoseCount: 0,
                PeaceCount: 0
            });
        }
        
        const playerStat = statsMap.get(playerName);
        
        // Update stats
        playerStat.WinChips += finalChips;
        playerStat.AttendCount += 1;
        
        if (finalChips > 0) {
            playerStat.WinCount += 1;
        } else if (finalChips < 0) {
            playerStat.LoseCount += 1;
        } else {
            playerStat.PeaceCount += 1;
        }
    });
    
    // Convert map to array and calculate winning rate
    let updatedStats = Array.from(statsMap.values()).map(stat => {
        return {
            ...stat,
            WinningRate: (stat.WinCount / stat.AttendCount * 100).toFixed(2) + "%"
        };
    });
    
    // Sort by WinChips and assign ranking
    updatedStats.sort((a, b) => b.WinChips - a.WinChips);
    updatedStats = updatedStats.map((stat, index) => {
        return {
            ...stat,
            Ranking: index + 1
        };
    });
    
    // Update player stats
    playerStats = updatedStats;
    
    // Update UI
    updateLeaderboard();
    generatePlayerList();
}

// Update leaderboard
function updateLeaderboard() {
    leaderboardTableBody.innerHTML = "";
    
    // Sort players by total chips
    const sortedPlayers = [...playerStats].sort((a, b) => b.WinChips - a.WinChips);
    
    // Find the index where WinChips becomes negative
    const zeroIndex = sortedPlayers.findIndex(player => player.WinChips <= 0);
    
    // Find max positive and negative values for color scaling
    const positiveChips = sortedPlayers.filter(player => player.WinChips > 0).map(player => player.WinChips);
    const negativeChips = sortedPlayers.filter(player => player.WinChips < 0).map(player => Math.abs(player.WinChips));
    
    const maxPositive = positiveChips.length > 0 ? Math.max(...positiveChips) : 0;
    const maxNegative = negativeChips.length > 0 ? Math.max(...negativeChips) : 0;
    
    // Update latest record time
    updateLatestRecordTime();
    
    // Insert player rows with appropriate background colors
    sortedPlayers.forEach((player, index) => {
        const row = document.createElement("tr");
        
        // Determine background color class based on WinChips
        let colorClass = '';
        if (player.WinChips > 0) {
            const ratio = player.WinChips / maxPositive;
            if (ratio > 0.8) colorClass = 'player-positive-max';
            else if (ratio > 0.6) colorClass = 'player-positive-3';
            else if (ratio > 0.4) colorClass = 'player-positive-2';
            else if (ratio > 0.2) colorClass = 'player-positive-1';
            else colorClass = 'player-positive';
        } else if (player.WinChips < 0) {
            const ratio = Math.abs(player.WinChips) / maxNegative;
            if (ratio > 0.8) colorClass = 'player-negative-max';
            else if (ratio > 0.6) colorClass = 'player-negative-3';
            else if (ratio > 0.4) colorClass = 'player-negative-2';
            else if (ratio > 0.2) colorClass = 'player-negative-1';
            else colorClass = 'player-negative';
        }
        
        row.className = colorClass;
        row.innerHTML = `
            <td class="ranking-cell">${index + 1}</td>
            <td class="player-name-cell">${player.Player}</td>
            <td>${player.WinningRate}</td>
            <td>${Math.round(player.WinChips)}</td>
            <td>${player.AttendCount}</td>
            <td>${player.WinCount}</td>
            <td>${player.LoseCount}</td>
            <td>${player.PeaceCount}</td>
        `;
        
        leaderboardTableBody.appendChild(row);
        
        // Insert water line row after the last positive WinChips player
        if (index === zeroIndex - 1) {
            const waterLineRow = document.createElement("tr");
            waterLineRow.className = "water-line-row";
            waterLineRow.innerHTML = `
                <td colspan="8" style="text-align: center; font-weight: bold; color: #2c3e50;">
                    Water Line
                </td>
            `;
            leaderboardTableBody.appendChild(waterLineRow);
        }
    });
}

// Add function to save leaderboard as image
async function saveLeaderboardAsImage() {
    const leaderboardContainer = document.querySelector('.leaderboard-container');
    
    try {
        // Use html2canvas to capture the leaderboard
        const canvas = await html2canvas(leaderboardContainer, {
            scale: 2, // Higher quality
            backgroundColor: '#ffffff',
            logging: false
        });

        // Convert canvas to blob
        const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
        
        // Create download link
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `leaderboard_${new Date().toISOString().split('T')[0]}.png`;
        
        // Trigger download
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    } catch (error) {
        console.error('Error saving leaderboard:', error);
        alert('Failed to save leaderboard image. Please try again.');
    }
}

// Reset game form
function resetGameForm() {
    document.getElementById("game-date").value = "";
    document.getElementById("service-fee").value = "";
    
    document.querySelectorAll(".attend-toggle").forEach(button => {
        button.textContent = "False";
        button.classList.remove("active");
    });
    
    document.querySelectorAll(".win-lose-toggle").forEach(button => {
        button.textContent = "Win";
        button.className = "toggle-button win-lose-toggle win";
    });
    
    document.querySelectorAll(".chip-input").forEach(input => {
        input.value = "0";
        input.disabled = true;
    });
    
    validationResult.classList.add("hidden");
    updateLeaderboardButton.disabled = true;
}

// Format date to "yyyy-MM-dd" format (changed from Chinese format)
function formatDate(dateString) {
    const date = new Date(dateString);
    const year = date.getFullYear();
    const month = (date.getMonth() + 1).toString().padStart(2, "0");
    const day = date.getDate().toString().padStart(2, "0");
    
    return `${year}-${month}-${day}`;
}

// Convert Chinese date format (yyyy年MM月dd日) to standard format (yyyy-MM-dd)
function convertChineseDateFormat(chineseDate) {
    if (!chineseDate || typeof chineseDate !== 'string') return chineseDate;
    
    // Check if the date is already in yyyy-MM-dd format
    if (/^\d{4}-\d{2}-\d{2}$/.test(chineseDate)) {
        return chineseDate;
    }
    
    // Extract year, month, and day from Chinese format
    const match = chineseDate.match(/(\d{4})年(\d{1,2})月(\d{1,2})日/);
    if (match) {
        const year = match[1];
        const month = match[2].padStart(2, "0");
        const day = match[3].padStart(2, "0");
        return `${year}-${month}-${day}`;
    }
    
    return chineseDate; // Return original if no match
}

// Search history records by date
function searchHistoryRecords() {
    const selectedDate = historyDateInput.value;
    
    if (!selectedDate) {
        alert("Please select a date to search records.");
        return;
    }
    
    // Format the date to match the format in records
    const formattedDate = formatDate(selectedDate);
    
    // Using standard format (yyyy-MM-dd) for comparison
    const recordsOnDate = gameRecords.filter(record => 
        convertChineseDateFormat(record.Time) === formattedDate
    );
    
    // Display results
    historyResult.classList.remove("hidden");
    selectedDateSpan.textContent = formattedDate;
    
    if (recordsOnDate.length === 0) {
        historyTableBody.innerHTML = "";
        noRecordsMessage.classList.remove("hidden");
        saveHistoryBtnContainer.classList.add("hidden"); // Hide save button when no records
        return;
    }
    
    // Hide no records message if we have records
    noRecordsMessage.classList.add("hidden");
    // Show save button when records are found
    saveHistoryBtnContainer.classList.remove("hidden");
    
    // Populate the history table
    historyTableBody.innerHTML = "";
    
    recordsOnDate.forEach(record => {
        const row = document.createElement("tr");
        
        // Convert Chinese Win/Lose status and set class accordingly
        let winLoseStatus = record.WinOrLose;
        let winLoseClass = "";
        
        if (winLoseStatus === "Win" || winLoseStatus === "水上") {
            winLoseStatus = "Win";
            winLoseClass = "win";
        } else if (winLoseStatus === "Lose" || winLoseStatus === "水下") {
            winLoseStatus = "Lose";
            winLoseClass = "lose";
        }
        
        row.innerHTML = `
            <td class="player-name-cell">${record.Player}</td>
            <td><span class="win-status ${winLoseClass}">${winLoseStatus}</span></td>
            <td>${record.Chips}</td>
            <td>${calculateServiceFee(record).toFixed(2)}</td>
            <td>${record.FinalChips}</td>
        `;
        
        historyTableBody.appendChild(row);
    });
}

// Helper function to calculate service fee from record
function calculateServiceFee(record) {
    const chips = parseFloat(record.Chips || 0);
    const finalChips = parseFloat(record.FinalChips || 0);
    
    // Service fee is the difference between chips and final chips
    return Math.max(0, chips - finalChips);
}

// Add new player
function addNewPlayer() {
    const newPlayerName = newPlayerNameInput.value.trim();
    
    if (!newPlayerName) {
        alert("Please enter a player name");
        return;
    }
    
    // Check if player already exists
    const existingPlayer = playerStats.find(player => 
        player.Player.toLowerCase() === newPlayerName.toLowerCase()
    );
    
    if (existingPlayer) {
        alert(`Player "${newPlayerName}" already exists!`);
        return;
    }
    
    // Add new player to playerStats
    const newPlayer = {
        Player: newPlayerName,
        Ranking: playerStats.length + 1,
        WinChips: 0,
        AttendCount: 0,
        WinCount: 0,
        LoseCount: 0,
        PeaceCount: 0,
        WinningRate: "0.00%"
    };
    
    playerStats.push(newPlayer);
    
    // Create player card for the new player
    createPlayerCard(newPlayer);
    
    // Reset input
    newPlayerNameInput.value = "";
    
    // Update leaderboard
    updateLeaderboard();
}

// Update leaderboard with new game data
async function updateLeaderboardWithNewData() {
    try {
        // First, reload game records to ensure we're working with the latest data
        await reloadGameRecords();
        
        // Check for duplicates
        const duplicateCheckResult = checkForDuplicates(currentGameData);
        
        if (duplicateCheckResult.canProceed) {
            // Prepare new records
            const newRecords = [];
            
            currentGameData.players.forEach(player => {
                newRecords.push({
                    Time: currentGameData.date,
                    ServiceFee_Rate: currentGameData.serviceFee,
                    Player: player.playerName,
                    Chips: player.chips,
                    WinOrLose: player.winOrLose === "Win" ? "Win" : "Lose",
                    Value: player.chips,
                    FinalChips: player.finalChips.toFixed(2)
                });
            });
            
            console.log(`Sending ${newRecords.length} records to server...`);
            
            // Send data to server for processing
            try {
                const response = await fetch('/update_leaderboard', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        newRecords: newRecords
                    })
                });
                
                console.log(`Server response status: ${response.status}`);
                
                if (!response.ok) {
                    throw new Error(`Server responded with ${response.status}: ${response.statusText}`);
                }
                
                const result = await response.json();
                console.log("Received response from server:", result);
                
                if (result.success) {
                    // Update local data with server response
                    gameRecords = result.gameRecords;
                    playerStats = result.playerStats;
                    
                    // Update UI to reflect new data
                    updateLeaderboard();
                    
                    // Show success message
                    alert("LeaderBoard has been successfully updated on the server!");
                    
                    // Disable the update button to prevent multiple updates
                    updateLeaderboardButton.disabled = true;
                    
                    // Switch to leaderboard section
                    switchSection("leaderboard-section");
                } else {
                    throw new Error(result.message || "Server update failed");
                }
            } catch (apiError) {
                console.error("API Error:", apiError);
                alert(`API Error: ${apiError.message}`);
            }
        }
    } catch (error) {
        console.error("Failed to update leaderboard:", error);
        alert(`Failed to update leaderboard: ${error.message}`);
    }
}

// Reload game records from CSV
async function reloadGameRecords() {
    try {
        const response = await fetch(RECORDS_CSV + "?_=" + new Date().getTime()); // Add cache-busting parameter
        const csvData = await response.text();
        
        // Parse CSV data
        return new Promise((resolve, reject) => {
            Papa.parse(csvData, {
                header: true,
                complete: (results) => {
                    gameRecords = results.data.filter(record => record.Time && record.Player); // Filter out empty rows
                    
                    // 保留原始格式，不进行格式转换
                    // 如果后续需要日期比较，再根据需要转换
                    
                    // 重新加载游戏记录后更新最新记录时间
                    updateLatestRecordTime();
                    
                    resolve(gameRecords);
                },
                error: (error) => {
                    reject(error);
                }
            });
        });
    } catch (error) {
        console.error("Failed to reload game records:", error);
        throw error;
    }
}

// Check for duplicates in game records
function checkForDuplicates(gameData) {
    const formattedDate = gameData.date;
    
    // Filter records with the same date
    const recordsWithSameDate = gameRecords.filter(record => record.Time === formattedDate);
    
    // Result object
    const result = {
        canProceed: true,
        message: ""
    };
    
    if (recordsWithSameDate.length > 0) {
        // Ask user if they want to update records with the same date
        const confirmUpdate = confirm(`There are already ${recordsWithSameDate.length} records with the date ${formattedDate}. Do you want to continue with the update?`);
        
        if (!confirmUpdate) {
            result.canProceed = false;
            result.message = "Update cancelled by user.";
            return result;
        }
        
        // Check for exact duplicates (same date, player, and chips)
        for (const player of gameData.players) {
            const exactDuplicates = recordsWithSameDate.filter(record => 
                record.Player === player.playerName && 
                parseFloat(record.Chips) === player.chips
            );
            
            if (exactDuplicates.length > 0) {
                result.canProceed = false;
                result.message = `Duplicate record found for player ${player.playerName} with same date and chips value. Cannot proceed with the update.`;
                alert(result.message);
                updateLeaderboardButton.disabled = true;
                return result;
            }
        }
    }
    
    return result;
}

// Convert array of objects to CSV string
function convertToCSV(objArray) {
    if (!objArray || objArray.length === 0) return "";
    
    const fields = Object.keys(objArray[0]);
    
    // Create header
    let csv = fields.join(",") + "\n";
    
    // Add records
    objArray.forEach(obj => {
        const values = fields.map(field => {
            const value = obj[field] !== undefined ? obj[field] : "";
            // Wrap values with commas or quotes in quotes
            return typeof value === 'string' && (value.includes(',') || value.includes('"')) 
                ? `"${value.replace(/"/g, '""')}"` 
                : value;
        });
        csv += values.join(",") + "\n";
    });
    
    return csv;
}

// Download CSV file
function downloadCSV(csv, filename) {
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    
    // Create a URL for the blob
    const url = URL.createObjectURL(blob);
    
    // Setup link properties
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    
    // Add link to document
    document.body.appendChild(link);
    
    // Click the link to trigger download
    link.click();
    
    // Cleanup
    document.body.removeChild(link);
}

// Update latest record time
function updateLatestRecordTime() {
    const latestUpdateTimeElement = document.getElementById("latest-update-time");
    
    if (!latestUpdateTimeElement) {
        console.error("Element with ID 'latest-update-time' not found");
        return;
    }
    
    console.log("Updating latest record time. Records count:", gameRecords ? gameRecords.length : 0);
    
    if (gameRecords && gameRecords.length > 0) {
        // 打印出前几条记录的时间格式，帮助调试
        console.log("Sample record dates:");
        for (let i = 0; i < Math.min(5, gameRecords.length); i++) {
            console.log(`Record ${i}:`, gameRecords[i].Time, typeof gameRecords[i].Time);
        }
        
        // 简化排序逻辑，直接比较字符串格式的日期（假设格式一致为yyyy-MM-dd）
        const sortedRecords = [...gameRecords].sort((a, b) => {
            // 直接比较字符串，因为yyyy-MM-dd格式可以直接按字典序比较
            if (a.Time > b.Time) return -1;
            if (a.Time < b.Time) return 1;
            return 0;
        });
        
        console.log("Sorted first record date:", sortedRecords[0]?.Time);
        
        // Get the latest record's date
        if (sortedRecords[0] && sortedRecords[0].Time) {
            const latestDate = sortedRecords[0].Time;
            console.log("Setting latest record date:", latestDate);
            latestUpdateTimeElement.textContent = latestDate;
        } else {
            console.warn("No valid date found in the first record");
            latestUpdateTimeElement.textContent = "No records found";
        }
    } else {
        console.warn("No game records found");
        latestUpdateTimeElement.textContent = "No records found";
    }
}

// Add function to save history records as image
async function saveHistoryAsImage() {
    const historyTable = document.querySelector('#history-section .table-container');
    const historyTitle = document.querySelector('#history-section h3');
    
    // Create a container to hold both title and table for the screenshot
    const container = document.createElement('div');
    container.style.backgroundColor = '#ffffff';
    container.style.padding = '20px';
    container.style.width = 'fit-content';
    
    // Clone the elements
    const titleClone = historyTitle.cloneNode(true);
    const tableClone = historyTable.cloneNode(true);
    
    // Add elements to container
    container.appendChild(titleClone);
    container.appendChild(tableClone);
    
    // Temporarily add to document
    document.body.appendChild(container);
    
    try {
        // Use html2canvas to capture the container
        const canvas = await html2canvas(container, {
            scale: 2, // Higher quality
            backgroundColor: '#ffffff',
            logging: false
        });
        
        // Remove temporary container
        document.body.removeChild(container);
        
        // Convert canvas to blob
        const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
        
        // Get the date from the title for the filename
        const date = selectedDateSpan.textContent;
        
        // Create download link
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `history_records_${date}.png`;
        
        // Trigger download
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    } catch (error) {
        console.error('Error saving history records:', error);
        alert('Failed to save history records image. Please try again.');
        // Make sure to remove container even if there's an error
        if (document.body.contains(container)) {
            document.body.removeChild(container);
        }
    }
} 