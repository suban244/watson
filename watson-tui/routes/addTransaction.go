package routes

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"path"
	"strconv"
	"time"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/huh"

	"github.com/suban244/watson/watson-tui/config"
)

type AddTransactionScreen struct {
	submission_underway bool
	form                *huh.Form
	message             any
}

func isFloat(s string) error {
	_, err := strconv.ParseFloat(s, 64)
	if err != nil {
		return errors.New("please enter a valid number")
	}
	return err
}

func nonEmpty(s string) error {
	if s == "" {
		return errors.New("please enter a value")
	}
	return nil
}

func isValidDate(s string) error {
	if s == "" {
		return nil
	}
	_, err := time.Parse(time.DateOnly, s)
	if err != nil {
		return err
	}
	return nil
}

func NewAddTransactionScreen() Screen {
	return AddTransactionScreen{
		form: huh.NewForm(
			huh.NewGroup(
				huh.NewInput().Title("Amount").Prompt("> ").Key("amount").Validate(isFloat),
				huh.NewInput().Title("Title").Prompt("> ").Key("title").Validate(nonEmpty),
				huh.NewInput().Title("Description").Prompt("> ").Key("description"),
				huh.NewConfirm().Title("Is it a Income?").Key("isIncome"),
			),
			huh.NewGroup(
				huh.NewMultiSelect[string]().Title("Tags").OptionsFunc(func() []huh.Option[string] {
					var options []huh.Option[string]
					tags := getAllTags()
					switch tags := tags.(type) {
					case getAllTagsMsg:
						for _, tag := range tags.Tags {
							options = append(options, huh.Option[string]{
								Value: tag.Id,
								Key:   tag.Name,
							})
						}
					}
					return options
				}, nil).Limit(3).Key("tags"),
			),
			huh.NewGroup(
				huh.NewSelect[string]().Options(
					huh.Option[string]{Key: "Today", Value: "today"},
					huh.Option[string]{Key: "Yesterday", Value: "yesterday"},
					huh.Option[string]{Key: "Custom", Value: "custom"}).Title("Date").Key("date"),
			),
			huh.NewGroup(
				huh.NewInput().Title("Custom Date").Prompt("> ").Key("customDate").Validate(isValidDate),
			),
		),
	}
}

func (m AddTransactionScreen) Init() tea.Cmd {
	cmds := []tea.Cmd{
		m.form.Init(),
	}
	return tea.Batch(cmds...)
}

func (m AddTransactionScreen) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	var cmds []tea.Cmd

	switch msg.(type) {
	case addANewTransactionFailedMsg:
		cmds = append(cmds, ReturnCmd())
	case addNewTransactionSuccessMsg:
		cmds = append(cmds, ReturnCmd())
	}

	form, cmd := m.form.Update(msg)
	if f, ok := form.(*huh.Form); ok {
		m.form = f
		cmds = append(cmds, cmd)
	}

	if m.form.State == huh.StateCompleted {
		amountString := m.form.GetString("amount")
		amount, err := strconv.ParseFloat(amountString, 32)
		if err != nil {
			m.message = err
			return m, tea.Batch(cmds...)
		}
		title := m.form.GetString("title")
		description := m.form.GetString("description")
		tagField := m.form.Get("tags")
		tags, ok := tagField.([]string)
		if !ok {
			m.message = tagField
		}

		isIncome := m.form.GetBool("isIncome")
		date_info := m.form.GetString("date")
		customDate := m.form.GetString("customDate")
		date := convertDate(date_info, customDate)

		transaction := Transaction{
			Amount:      amount,
			Title:       title,
			Description: description,
			Tags:        tags,
			IsIncome:    isIncome,
			Date:        date,
		}

		if !m.submission_underway {
			cmds = append(cmds, createCmdAddTransaction(transaction))
			m.submission_underway = true
		}
	}

	return m, tea.Batch(cmds...)
}

func (m AddTransactionScreen) View() string {

	switch m.form.State {
	case huh.StateCompleted:
		return fmt.Sprintf("%T", m.message)
	default:
		return m.form.View()
	}
}

type Transaction struct {
	Amount      float64  `json:"amount"`
	Title       string   `json:"title"`
	Description string   `json:"description"`
	Tags        []string `json:"tags"`
	IsIncome    bool     `json:"is_income"`
	Date        string   `json:"date"`
}

type addANewTransactionFailedMsg struct {
	Err error
}

type addNewTransactionSuccessMsg struct {
	Transaction Transaction
}

func createCmdAddTransaction(transaction Transaction) tea.Cmd {
	return func() tea.Msg {
		u, err := url.Parse(config.SERVER_URL)
		if err != nil {
			return addANewTransactionFailedMsg{Err: err}
		}
		u.Path = path.Join(u.Path, "transaction")
		u.Path = u.Path + "/"

		data, err := json.Marshal(transaction)
		if err != nil {
			return addANewTransactionFailedMsg{Err: err}
		}

		client := &http.Client{}
		res, err := client.Post(u.String(), "application/json", bytes.NewBuffer(data))

		if err != nil {
			return addANewTransactionFailedMsg{Err: err}
		}

		defer res.Body.Close()
		body, err := io.ReadAll(res.Body)
		if err != nil {
			return addANewTransactionFailedMsg{Err: err}
		}

		if res.StatusCode != http.StatusOK {
			return addANewTransactionFailedMsg{Err: fmt.Errorf("error creating tag")}
		}

		var responseTransaction Transaction
		err = json.Unmarshal(body, &responseTransaction)
		if err != nil {
			return addANewTransactionFailedMsg{Err: err}
		}
		return addNewTransactionSuccessMsg{Transaction: responseTransaction}
	}
}

func convertDate(date_info string, customDate string) string {
	if date_info == "today" {
		return time.Now().Format(time.DateOnly)
	} else if date_info == "yesterday" {
		return time.Now().AddDate(0, 0, -1).Format(time.DateOnly)
	}
	return customDate
}
