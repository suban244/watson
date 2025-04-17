package routes

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"path"
	"time"

	"github.com/charmbracelet/bubbles/table"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/suban244/watson/watson-tui/config"
)

type ViewTransactionScreen struct {
	failedGettingTransaction bool
	err                      error
	transactions             []Transaction
	table                    table.Model
}

var baseStyle = lipgloss.NewStyle().
	BorderStyle(lipgloss.NormalBorder()).
	BorderForeground(lipgloss.Color("240"))

func NewViewTransactionsScreen() Screen {
	columns := []table.Column{
		{Title: "Date", Width: 20},
		{Title: "Title", Width: 20},
		{Title: "Description", Width: 20},
		{Title: "Amount", Width: 20},
		{Title: "Tags", Width: 20},
	}
	s := table.DefaultStyles()
	s.Header = s.Header.
		BorderStyle(lipgloss.NormalBorder()).
		BorderForeground(lipgloss.Color("240")).
		BorderBottom(true).
		Bold(false)
	s.Selected = s.Selected.
		Foreground(lipgloss.Color("229")).
		Background(lipgloss.Color("57")).
		Bold(false)

	t := table.New(
		table.WithColumns(columns),
		table.WithFocused(true),
	)
	t.SetStyles(s)
	return ViewTransactionScreen{
		table: t,
	}
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
		m.table.SetRows(
			transactionListToRows(msg.transactions),
		)

	case tea.KeyMsg:
		t, cmd := m.table.Update(msg)
		m.table = t
		return m, cmd

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
	return baseStyle.Render(m.table.View()) + "\n"
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

func transactionListToRows(transactions []Transaction) []table.Row {
	var rows []table.Row
	for _, transaction := range transactions {
		dateFormat := "2006-01-02T15:04:05"
		date, err := time.Parse(dateFormat, transaction.Date)
		if err != nil {
			continue
		}
		row := []string{
			fmt.Sprint(date.Format("2006-01-02")),
			transaction.Title,
			transaction.Description,
			fmt.Sprintf("%.2f", transaction.Amount),
			fmt.Sprintf("%v", transaction.Tags),
		}
		rows = append(rows, row)
	}
	return rows
}
