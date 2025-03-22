package routes

import tea "github.com/charmbracelet/bubbletea"

type Screen interface {
	Init() tea.Cmd
	Update(msg tea.Msg) (tea.Model, tea.Cmd)
	View() string
}

type ScreenCreator func() Screen

type Route struct {
	Title        string
	CreateScreen ScreenCreator
}

type ReturnMsg struct{}

func ReturnCmd() tea.Cmd {
	return func() tea.Msg {
		return ReturnMsg{}
	}
}
