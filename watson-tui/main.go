package main

import (
	"fmt"
	"os"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	routes "github.com/suban244/watson/watson-tui/routes"
)

type Styles struct {
	BorderColor lipgloss.Color
}

func DefaultStyles() *Styles {
	s := new(Styles)
	s.BorderColor = lipgloss.Color("36")

	return s

}

type model struct {
	routes []routes.Route
	stack  []routes.Screen

	cursor int
	styles *Styles
}

func initialModel() model {
	routes := []routes.Route{
		{
			Title:        "Add a new Transaction",
			CreateScreen: routes.NewAddTransactionScreen,
		},
		{
			Title:        "Add a new Tag",
			CreateScreen: routes.NewAddTagScreen,
		},
		{
			Title:        "View Transactions",
			CreateScreen: routes.NewViewTransactionsScreen,
		},
	}
	styles := DefaultStyles()
	return model{
		routes: routes,
		styles: styles,
	}
}

func (m model) Init() tea.Cmd {
	return tea.ClearScreen
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.String() {
		case "ctrl+c":
			return m, tea.Quit

		case "esc":
			if len(m.stack) > 0 {
				m.stack = m.stack[:len(m.stack)-1]
				return m, nil
			}
		}

	// Does it make sense for say a returnMsg should only be handled by the main model?
	// or should it be handled by whatever is the 2nd last screen in the stack?
	case routes.ReturnMsg:
		if len(m.stack) > 0 {
			m.stack = m.stack[:len(m.stack)-1]
		}
		return m, nil
	}

	if len(m.stack) == 0 {
		var cmd tea.Cmd
		switch msg := msg.(type) {
		case tea.KeyMsg:
			switch msg.String() {
			case "up", "k":
				if m.cursor > 0 {
					m.cursor--
				}

			case "down", "j":
				if m.cursor < len(m.routes)-1 {
					m.cursor++
				}

			case "enter", " ":
				route := m.routes[m.cursor]
				m.stack = append(m.stack, route.CreateScreen())
				cmd = m.stack[len(m.stack)-1].Init()
			}
		}
		return m, cmd
	} else {
		route := m.stack[len(m.stack)-1]
		nextModel, cmd := route.Update(msg)
		m.stack[len(m.stack)-1] = nextModel
		return m, cmd
	}

}
func (m model) View() string {
	if len(m.stack) == 0 {

		s := "Here are the options? \n\n"

		for i, option := range m.routes {
			cursor := " "
			if m.cursor == i {
				cursor = ">"
			}
			s += fmt.Sprintf("%s %s\n", cursor, option.Title)
		}

		s += "\nPress q to quit.\n"

		return s
	} else {
		route := m.stack[len(m.stack)-1]
		return route.View()
	}
}

func main() {
	p := tea.NewProgram(initialModel())
	if _, err := p.Run(); err != nil {
		fmt.Printf("Alas, there's been an error: %v", err)
		os.Exit(1)
	}
}
