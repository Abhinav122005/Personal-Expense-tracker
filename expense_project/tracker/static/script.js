document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('expense-form');
    const expenseList = document.getElementById('expense-list');
    const totalBalanceElement = document.getElementById('total-balance');
    const clearButton = document.getElementById('clear-expenses-btn');
    let totalSpent = 0.0; // Initialize totalSpent as a float

    // --- Helper function to get Django's CSRF token ---
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.startsWith(name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    const csrftoken = getCookie('csrftoken');
    // ----------------------------------------------------

    // Initial load and event listeners
    fetchInitialExpenses();
    form.addEventListener('submit', handleFormSubmit);
    clearButton.addEventListener('click', handleClearExpenses);

    // 1. GET: Fetch existing expenses from the Django API
    function fetchInitialExpenses() {
        fetch('/api/expenses/')
            .then(response => {
                if (!response.ok) throw new Error('Failed to fetch expenses.');
                return response.json();
            })
            .then(initialExpenses => {
                initialExpenses.forEach(expense => {
                    // IMPORTANT: Parse amount from string (Django returns Decimal as string)
                    const amount = parseFloat(expense.amount); 
                    addExpenseToDOM(expense.description, amount, expense.category);
                    updateTotal(amount);
                });
            })
            .catch(error => console.error('Error fetching initial expenses:', error));
    }

    // 2. POST: Handle form submission to add a new expense
    function handleFormSubmit(event) {
        event.preventDefault();

        const description = document.getElementById('description').value;
        const amount = parseFloat(document.getElementById('amount').value);
        const category = document.getElementById('category').value;

        if (isNaN(amount) || amount <= 0) {
            alert('Please enter a valid positive amount.');
            return;
        }

        const newExpense = {
            description: description,
            amount: amount.toFixed(2), // Send as string for Django to handle Decimal conversion
            category: category
        };

        fetch('/api/expenses/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken // Include CSRF Token
            },
            body: JSON.stringify(newExpense)
        })
        .then(response => {
            if (response.status === 201) return response.json();
            throw new Error('Failed to add expense. Status: ' + response.status);
        })
        .then(data => {
            // SUCCESS: data.amount is a string, parse it before use
            const savedAmount = parseFloat(data.amount); 
            
            // This is the line that updates the UI:
            addExpenseToDOM(data.description, savedAmount, data.category);
            
            updateTotal(savedAmount);
            form.reset();
        })
        .catch(error => console.error('Error submitting expense:', error));
    }
    
    // 3. DELETE: Handle clearing all expenses
    function handleClearExpenses() {
        if (!confirm("Are you sure you want to clear ALL expenses? This cannot be undone.")) {
            return;
        }

        fetch('/api/expenses/', {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': csrftoken
            }
        })
        .then(response => {
            if (response.status === 204) {
                // Clear the UI elements
                expenseList.innerHTML = '';
                totalSpent = 0.0;
                totalBalanceElement.textContent = 'Total Spent: $0.00';
            } else {
                throw new Error('Failed to clear expenses.');
            }
        })
        .catch(error => console.error('Error clearing expenses:', error));
    }
    
    // UI Helpers
    function addExpenseToDOM(description, amount, category) {
        // Ensures expenseList element exists before trying to manipulate it
        if (!expenseList) { return; } 

        const listItem = document.createElement('li');
        listItem.innerHTML = `
            <div class="expense-details">
                <strong>${description}</strong>
                <p>Category: ${category}</p>
            </div>
            <div class="expense-amount">
                -$${amount.toFixed(2)} 
            </div>
        `;
        expenseList.prepend(listItem);
    }

    function updateTotal(latestAmount) {
        totalSpent += latestAmount;
        totalBalanceElement.textContent = `Total Spent: $${totalSpent.toFixed(2)}`;
    }
});