package routes

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"path"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/suban244/watson/watson-tui/config"
)

type ViewTransactionScreen struct {
	failedGettingTransaction bool
	err                      error
	transactions             []Transaction
}

func NewViewTransactionsScreen() Screen {
	return ViewTransactionScreen{}
}

func (m ViewTransactionScreen) Init() tea.Cmd {
	return createCmdViewTransaction()
}

func (m ViewTransactionScreen) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case viewTransactionFailedMsg:
		m.failedGettingTransaction = true
		m.err = msg.err
	case viewTransactionSuccessMsg:
		m.transactions = msg.transactions
	}
	return m, nil
}

func (m ViewTransactionScreen) View() string {
	if m.failedGettingTransaction {
		return m.err.Error()
	}
	if len(m.transactions) == 0 {
		return "No transactions found"
	}
	var s string
	for _, t := range m.transactions {
		s += fmt.Sprintf("Amount: %d\nTitle: %s\nDescription: %s\nDate: %s\n\n", t.Amount, t.Title, t.Description, t.Date)
	}
	return s
}

type viewTransactionFailedMsg struct{ err error }
type viewTransactionSuccessMsg struct {
	transactions []Transaction
}

func createCmdViewTransaction() tea.Cmd {
	return func() tea.Msg {
		u, err := url.Parse(config.SERVER_URL)
		if err != nil {
			return viewTransactionFailedMsg{err: err}
		}

		u.Path = path.Join(u.Path, "transaction", "list")

		client := &http.Client{}
		res, err := client.Get(u.String())
		if err != nil {
			return viewTransactionFailedMsg{err: err}
		}
		defer res.Body.Close()

		var transactions []Transaction
		body, err := io.ReadAll(res.Body)
		if err != nil {
			return viewTransactionFailedMsg{err: err}
		}

		if res.StatusCode != http.StatusOK {
			return viewTransactionFailedMsg{err: fmt.Errorf("body: %s", body)}
		}

		if err := json.Unmarshal(body, &transactions); err != nil {
			return viewTransactionFailedMsg{err: err}
		}

		return viewTransactionSuccessMsg{transactions: transactions}
	}
}
